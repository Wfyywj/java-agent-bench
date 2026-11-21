import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("upstream", ROOT / "upstream/bench.py")
upstream = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(upstream)

SOURCE = "lib/src/main/java/sample/Counter.java"
BASE = b"package sample; public class Counter { public static int next() { return 0; } }"
FIX = BASE.replace(b"return 0", b"return 1")
PROBE = """
import sample.Counter;
public class Probe {
    public static void main(String[] args) {
        if (Counter.next() != 1) {
            System.out.println("FAIL expected one");
            System.exit(1);
        }
        System.out.println("PASS expected one");
    }
}
"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


class UpstreamCliTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.work = root / "candidate"
        task_dir = root / "upstream" / "GH99"
        task_dir.mkdir(parents=True)
        base_commit, fix_commit = "a" * 40, "b" * 40
        prefix = "https://raw.githubusercontent.com/example/project/"
        self.base_url = f"{prefix}{base_commit}/{SOURCE}"
        self.fix_url = f"{prefix}{fix_commit}/{SOURCE}"
        jar_url = "https://repo.maven.apache.org/maven2/example/fixture.jar"
        jar = io.BytesIO()
        with zipfile.ZipFile(jar, "w") as archive:
            archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n\n")
        self.assets = {self.base_url: BASE, self.fix_url: FIX, jar_url: jar.getvalue()}
        task = {
            "id": "GH99", "title": "Counter", "scenario": "Return the next value.",
            "repository": "example/project", "issue": 1,
            "issue_url": "https://github.com/example/project/issues/1",
            "fix_url": "https://github.com/example/project/pull/2",
            "license": "MIT", "license_url": "https://example.org/LICENSE",
            "baseline_commit": base_commit, "fixed_commit": fix_commit,
            "acceptance": ["next() returns one."],
            "sources": [{"path": SOURCE, "baseline_sha256": digest(BASE), "fixed_sha256": digest(FIX)}],
            "dependencies": [{"url": jar_url, "sha256": digest(jar.getvalue())}],
        }
        (task_dir / "task.json").write_text(json.dumps(task), encoding="utf-8")
        (task_dir / "Probe.java").write_text(PROBE, encoding="utf-8")
        self.enter_patch(patch.object(upstream, "TASKS", task_dir.parent))
        self.enter_patch(patch.object(upstream, "urlopen", self.open_asset))

    def enter_patch(self, patcher):
        patcher.start()
        self.addCleanup(patcher.stop)

    def open_asset(self, url, *, timeout):
        return io.BytesIO(self.assets[url])

    def cli(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        argv = ["upstream.py", *(str(arg) for arg in arguments)]
        with patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = upstream.main()
            except SystemExit as exc:  # argparse reports usage errors this way.
                code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def prepare(self):
        code, _, error = self.cli("prepare", "GH99", self.work)
        self.assertEqual(code, 0, error)

    def evaluate(self):
        return self.cli("evaluate", "GH99", self.work, "--trusted-code")

    def test_prepare_hash_failure_allows_retry_and_preserves_existing_work(self):
        self.assets[self.base_url] = b"partial download"
        code, _, error = self.cli("prepare", "GH99", self.work)
        self.assertEqual(code, 2)
        self.assertIn("SHA-256", error)
        self.assertFalse(self.work.exists())
        self.assets[self.base_url] = BASE
        self.prepare()
        source = self.work / SOURCE
        self.assertEqual(source.read_bytes(), BASE)
        self.assertFalse((self.work / "Probe.java").exists())
        source.write_bytes(FIX)
        self.assertEqual(self.cli("prepare", "GH99", self.work)[0], 2)
        self.assertEqual(source.read_bytes(), FIX)

    def test_rejects_wrong_workspace_or_modified_dependency(self):
        self.prepare()
        self.assertEqual(self.cli("evaluate", "GH99", self.work)[0], 2)
        marker = self.work / "PREPARED.json"
        original = marker.read_bytes()
        stale = json.loads(original)
        stale["baseline_commit"] = "c" * 40
        marker.write_text(json.dumps(stale), encoding="utf-8")
        self.assertEqual(self.evaluate()[0], 2)
        marker.write_bytes(original)
        (self.work / ".deps/fixture.jar").write_bytes(b"modified")
        code, _, error = self.evaluate()
        self.assertEqual(code, 2)
        self.assertIn("SHA-256", error)

    def test_evaluation_distinguishes_a_regression_a_crash_and_a_fix_offline(self):
        self.prepare()
        self.assets.clear()  # Any attempt to download when evaluating will fail the test.
        source = self.work / SOURCE
        code, out, err = self.evaluate()
        self.assertEqual(code, 1, err)
        self.assertIn("FAIL expected one", out)
        source.write_bytes(BASE.replace(b"return 0", b"throw new IllegalStateException()"))
        code, _, err = self.evaluate()
        self.assertEqual(code, 2)
        self.assertIn("IllegalStateException", err)
        source.write_bytes(FIX)
        code, out, err = self.evaluate()
        self.assertEqual(code, 0, err)
        self.assertIn("PASS expected one", out)


if __name__ == "__main__":
    unittest.main()
