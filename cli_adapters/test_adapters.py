import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cli_adapters.__main__ import main
from cli_adapters.collection import collect, snapshot
from cli_adapters.common import AdapterError, read_regular, sha256
from cli_adapters.normalize import normalize
from cli_adapters.plans import plan


def trace(*events):
    return ("\n".join(json.dumps(e) for e in events) + "\n").encode()


def norm(provider, raw):
    return normalize(provider, raw, model="synthetic-model", cli_version="synthetic-version", data_class="synthetic_test_fixture")


class NormalizeTests(unittest.TestCase):
    def test_fixtures_not_trials(self):
        for provider in ["codex", "claude"]:
            raw = (Path(__file__).parent / "fixtures" / (provider + ".synthetic.jsonl")).read_bytes()
            out = norm(provider, raw)
            self.assertEqual(out["cli_outcome"], "completed")
            self.assertEqual(out["usage"]["input_tokens"], 100)
            self.assertEqual(out["usage"]["output_tokens"], 10)
            self.assertEqual(out["raw_trace_sha256"], sha256(raw))
            self.assertFalse(out["analysis_record_ready"])
            self.assertNotEqual(out["run_kind"], "agent_trial")
            self.assertEqual(out["business_status"], "not_evaluated")

    def test_process_and_cost_observation_semantics(self):
        for provider, event in [("codex", {"type": "turn.completed"}), ("claude", {"type": "result", "subtype": "success", "is_error": False, "total_cost_usd": 0.001})]:
            out = norm(provider, trace(event))
            self.assertIsNone(out["process_exit_code"])
            self.assertEqual(out["process_status"], "not_supplied")
            self.assertEqual(out["cli_outcome_basis"], "terminal_event_only")
            self.assertTrue(any("not a verified process exit" in item for item in out["warnings"]))
            self.assertEqual(out["cost_semantics"], "cli_reported_estimate_not_verified_billing" if provider == "claude" else "unknown_not_reported")
            self.assertEqual(out["business_status"], "not_evaluated")
            self.assertFalse(out["analysis_record_ready"])
        missing = norm("claude", trace({"type": "result", "subtype": "success", "is_error": False}))
        self.assertEqual(missing["cost_semantics"], "unknown_not_reported")

    def test_missing_usage_is_unknown(self):
        out = norm("codex", trace({"type": "turn.completed"}))
        self.assertIsNone(out["cost_usd"])
        self.assertTrue(all(value is None for value in out["usage"].values()))

    def test_failure_and_partial(self):
        self.assertEqual(norm("codex", trace({"type": "turn.failed", "error": {"message": "fixture"}}))["cli_outcome"], "failed")
        for raw in [b"", trace({"type": "error", "message": "fixture"}), trace({"type": "turn.started"})]:
            self.assertEqual(norm("codex", raw)["cli_outcome"], "incomplete")
        for subtype, error in [("success", True), ("error_max_turns", True), ("error_during_execution", False)]:
            self.assertEqual(norm("claude", trace({"type": "result", "subtype": subtype, "is_error": error}))["cli_outcome"], "failed")

    def test_duplicate_terminal_count_once(self):
        event = {"type": "turn.completed", "usage": {"input_tokens": 3, "output_tokens": 1}}
        out = norm("codex", trace(event, event))
        self.assertEqual(out["usage"]["input_tokens"], 3)
        self.assertEqual(out["terminal_record_count"], 2)
        with self.assertRaisesRegex(AdapterError, "ambiguous"):
            norm("codex", trace(event, {"type": "turn.failed"}))
        with self.assertRaisesRegex(AdapterError, "ambiguous"):
            norm("codex", trace(event, {"type": "turn.started"}))

    def test_partial_session_concatenation_rejected(self):
        with self.assertRaisesRegex(AdapterError, "ambiguous"):
            norm("codex", trace({"type": "thread.started", "thread_id": "one"}, {"type": "turn.started"}, {"type": "thread.started", "thread_id": "two"}, {"type": "turn.completed"}))
        with self.assertRaisesRegex(AdapterError, "ambiguous"):
            norm("codex", trace({"type": "turn.started"}, {"type": "turn.started"}, {"type": "turn.completed"}))
        with self.assertRaisesRegex(AdapterError, "ambiguous"):
            norm("claude", trace({"type": "system", "subtype": "init", "session_id": "one"}, {"type": "assistant", "session_id": "two"}))
        with self.assertRaisesRegex(AdapterError, "ambiguous"):
            norm("claude", trace({"type": "system", "subtype": "init"}, {"type": "system", "subtype": "init"}))

    def test_malformed(self):
        for raw in [b'{', b'[]', b'{"type":"x","type":"y"}', b'{"type":"x","v":NaN}', b'\xff', b'{"type":3}', b'{"type":"turn.completed","future":1e999}']:
            with self.subTest(raw=raw), self.assertRaises(AdapterError):
                norm("codex", raw)
        for value in [-1, True, 1.2, "12"]:
            with self.assertRaises(AdapterError):
                norm("codex", trace({"type": "turn.completed", "usage": {"input_tokens": value}}))
        with self.assertRaises(AdapterError):
            norm("claude", trace({"type": "result", "subtype": "success"}))
        with self.assertRaises(AdapterError):
            norm("codex", trace({"type": "turn.completed", "usage": {"input_tokens": 1, "cached_input_tokens": 2}}))

    def test_large_integer_does_not_overflow_float_conversion(self):
        out = norm("codex", trace({"type": "turn.completed", "usage": {"input_tokens": 10 ** 400}}))
        self.assertEqual(out["usage"]["input_tokens"], 10 ** 400)

    def test_unknown_fields_preserved_and_zero_means_measured(self):
        event = {"type": "result", "subtype": "success", "is_error": False, "new_field": {"x": 1}, "usage": {"input_tokens": 0, "future": 8}, "total_cost_usd": 0}
        out = norm("claude", trace({"type": "future_event", "extra": 1}, event))
        self.assertEqual(out["terminal_metadata"]["new_field"], {"x": 1})
        self.assertEqual(out["unknown_event_types"], ["future_event"])
        self.assertEqual(out["cost_usd"], 0)
        self.assertIsNone(out["cost_usd_unknown_reason"])
        self.assertIsNone(out["usage"]["output_tokens"])

    def test_stream_and_model_totals_never_added(self):
        out = norm("claude", trace({"type": "assistant", "message": {"usage": {"input_tokens": 900}}}, {"type": "stream_event", "event": {"usage": {"output_tokens": 900}}}, {"type": "result", "subtype": "success", "is_error": False, "usage": {"input_tokens": 10, "output_tokens": 2}, "modelUsage": {"m": {"inputTokens": 10}}}))
        self.assertEqual(out["usage"]["input_tokens"], 10)
        self.assertEqual(out["usage"]["output_tokens"], 2)

    def test_actual_trials_cannot_be_asserted(self):
        with self.assertRaises(AdapterError):
            normalize("codex", b"", model="m", cli_version="v", data_class="actual_agent_trials")


class FilesAndPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.before, self.after = self.root / "before", self.root / "after"
        self.before.mkdir()
        self.after.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_plan_never_launches(self):
        with patch("subprocess.Popen", side_effect=AssertionError("must not execute")), patch("os.system", side_effect=AssertionError("must not execute")), patch("os.posix_spawn", side_effect=AssertionError("must not execute")):
            for provider in ["codex", "claude"]:
                out = plan(provider, self.before, "model-id", "version-id", "$(touch /tmp/not-allowed); secret prompt")
                self.assertEqual(out["execution_status"], "not_run")
                self.assertFalse(out["launch_supported"])
                self.assertNotIn("secret prompt", json.dumps(out))
                self.assertNotIn("--dangerously-skip-permissions", out["argv"])
                self.assertNotIn("--ignore-rules", out["argv"])
                self.assertNotIn("--bare", out["argv"])
                self.assertNotIn("resume", out["argv"])

    def test_invalid_plan_and_cli_has_no_run_mode(self):
        for kwargs in [{"model": "--bad"}, {"cli_version": ""}, {"auth_mode": "my-secret"}, {"sandbox": "danger-full-access"}]:
            args = dict(provider="codex", workspace=self.before, model="m", cli_version="v", prompt="p")
            args.update(kwargs)
            with self.assertRaises(AdapterError):
                plan(**args)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["run"])

    def test_diff_add_delete_binary_no_newline(self):
        (self.before / "deleted.java").write_text("old\n")
        (self.before / "changed.java").write_text("old")
        (self.after / "changed.java").write_text("new")
        (self.after / "new.bin").write_bytes(b"\x00\xff")
        out = collect(self.before, self.after)
        self.assertEqual([c["kind"] for c in out["changes"]], ["modified", "deleted", "added"])
        self.assertIn("No newline at end of file", out["changes"][0]["text_diff"])
        self.assertIsNone(out["changes"][2]["text_diff"])
        self.assertFalse(out["uploaded"])
        self.assertEqual(snapshot(self.before)[0], out["before"])

    def test_symlink_escape_rejected(self):
        target = self.root / "private"
        target.write_text("must-not-read")
        (self.before / "escape").symlink_to(target)
        with self.assertRaises((AdapterError, OSError)):
            snapshot(self.before)
        with self.assertRaises((AdapterError, OSError)):
            read_regular(self.before / "escape")
        (self.root / "linked").symlink_to(self.after, target_is_directory=True)
        with self.assertRaises((AdapterError, OSError)):
            plan("codex", self.root / "linked", "m", "v", "p")

    def test_parent_symlink_swap_rejected(self):
        from cli_adapters import common
        folder, outside = self.root / "selected", self.root / "outside"
        folder.mkdir()
        outside.mkdir()
        (folder / "file").write_text("inside")
        (outside / "file").write_text("outside")
        original = common.checked_path
        def swap(path):
            checked = original(path)
            folder.rename(self.root / "old-selected")
            folder.symlink_to(outside, target_is_directory=True)
            return checked
        with patch.object(common, "checked_path", side_effect=swap), self.assertRaises(OSError):
            read_regular(folder / "file")

    def test_special_and_oversize_rejected(self):
        os.mkfifo(self.before / "fifo")
        with self.assertRaises(AdapterError):
            snapshot(self.before)
        (self.before / "fifo").unlink()
        with (self.before / "big").open("wb") as f:
            f.truncate(1024 * 1024 + 1)
        with self.assertRaises(AdapterError):
            snapshot(self.before)
        with self.assertRaises(AdapterError):
            read_regular(self.before / "big")

    def test_nested_roots_rejected(self):
        child = self.before / "nested"
        child.mkdir()
        for target in [self.before, child]:
            with self.assertRaises(AdapterError):
                collect(self.before, target)

    def test_cli_plan(self):
        prompt = self.root / "prompt.txt"
        prompt.write_text("SYNTHETIC prompt")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), patch("subprocess.Popen", side_effect=AssertionError("must not execute")):
            code = main(["plan", "--provider", "codex", "--workspace", str(self.before), "--model", "synthetic-model", "--cli-version", "0.164.0", "--prompt-file", str(prompt)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["execution_status"], "not_run")


if __name__ == "__main__":
    unittest.main()
