"""Trusted local preparation fixtures, not model results or billing tests."""
import contextlib
import io
import json
import os
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiment_tools.__main__ import main
from experiment_tools.workspace import initialize, status, doctor, ROOT


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.work = self.base/'run'

    def init(self, **overrides):
        args = dict(task='B01-slice', provider='codex', model='explicit-test-model',
                    cli_version='explicit-test-version', workspace=str(self.work))
        args.update(overrides)
        return initialize(**args)

    def test_independent_identical_snapshots_and_provenance(self):
        result = self.init(sandbox='workspace-write')
        self.assertEqual(result['implementation_id'], 'B01-slice')
        left, right = self.work/'baseline/src/Main.java', self.work/'candidate/src/Main.java'
        self.assertEqual(left.read_bytes(), right.read_bytes())
        self.assertNotEqual(left.stat().st_ino, right.stat().st_ino)
        right.write_text('edited fixture')
        self.assertNotEqual(left.read_bytes(), right.read_bytes())
        manifest = json.loads((self.work/'manifest.json').read_text())
        self.assertEqual(manifest['execution_status'], 'not_run')
        self.assertIsNone(manifest['cost_usd'])
        self.assertEqual(manifest['metadata_provenance'], 'caller_declared_not_probed')
        self.assertFalse((self.work/'candidate/reference').exists())
        self.assertFalse((self.work/'candidate/verifier').exists())
        plan = json.loads((self.work/'command-plan.json').read_text())
        self.assertIn('workspace-write', plan['argv'])
        self.assertFalse(plan['launch_supported'])

    def test_status_missing_evidence_and_changes(self):
        self.init()
        report = status(self.work)
        self.assertEqual(len(report['missing_evidence']), 4)
        self.assertTrue(all(i['status'] == 'unchanged' for i in report['integrity']))
        (self.work/'candidate/src/Main.java').write_text('change')
        (self.work/'baseline/src/Main.java').write_text('tamper')
        report = status(self.work)
        self.assertEqual([i['status'] for i in report['integrity'][-2:]], ['changed', 'changed'])

    def test_present_fake_success_never_passes(self):
        self.init()
        for name in ('trace.jsonl', 'normalized-trace.json', 'collection.json', 'evaluation.json'):
            (self.work/name).write_text('{"passed":true,"cost_usd":0}')
        report = status(self.work)
        self.assertEqual(report['missing_evidence'], [])
        self.assertEqual(report['business_status'], 'not_evaluated')
        self.assertEqual(report['execution_status'], 'not_verified')
        self.assertIsNone(report['cost_usd'])

    def test_empty_evidence_is_missing(self):
        self.init()
        (self.work/'trace.jsonl').write_text('  \n')
        self.assertIn('trace.jsonl', status(self.work)['missing_evidence'])

    def test_existing_never_overwritten(self):
        self.work.mkdir()
        (self.work/'keep').write_text('safe')
        with self.assertRaises(ValueError): self.init()
        self.assertEqual((self.work/'keep').read_text(), 'safe')

    def test_existing_file_never_overwritten(self):
        self.work.write_text('safe')
        with self.assertRaises(ValueError): self.init()
        self.assertEqual(self.work.read_text(), 'safe')

    def test_invalid_task_and_option_fail_before_creation(self):
        for args in ({'task':'../B01'}, {'task':'B01-slice-slice'}, {'task':'B99'},
                     {'model':'-bad'}, {'model':''}, {'cli_version':'x\nsecret'},
                     {'provider':'other'}, {'provider':'claude', 'sandbox':'workspace-write'}):
            with self.subTest(args=args), self.assertRaises(ValueError): self.init(**args)
            self.assertFalse(self.work.exists())

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError): self.init(workspace=self.base/'x/../run')
        self.assertFalse(self.work.exists())

    def test_repo_destination_rejected(self):
        with self.assertRaises(ValueError): self.init(workspace=ROOT/'not-created-experiment-test')

    def test_parent_must_exist(self):
        with self.assertRaises(ValueError): self.init(workspace=self.base/'missing/run')
        self.assertFalse((self.base/'missing').exists())

    def test_symlink_parent_rejected(self):
        (self.base/'link').symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(ValueError): self.init(workspace=self.base/'link/run')

    def test_symlink_destination_rejected(self):
        self.work.symlink_to(self.base/'absent')
        with self.assertRaises(ValueError): self.init()

    def test_status_symlink_evidence_rejected(self):
        self.init()
        (self.base/'secret').write_text('do not follow')
        (self.work/'trace.jsonl').symlink_to(self.base/'secret')
        with self.assertRaises(ValueError): status(self.work)

    def test_status_manifest_injection_rejected(self):
        self.init()
        path = self.work/'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['artifacts_sha256'] = {'../../secret': 'x'}
        path.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError): status(self.work)

    def test_status_identity_tamper_rejected(self):
        self.init()
        path = self.work/'manifest.json'
        original = json.loads(path.read_text())
        for changes in ({'implementation_id':'K05-slice'},
                        {'task_id':'K05', 'implementation_id':'K05-slice', 'manifest_sha256':'0'*64},
                        {'manifest_sha256':'invalid'}, {'task_id':'../B01'}):
            manifest = dict(original, **changes)
            path.write_text(json.dumps(manifest))
            with self.subTest(changes=changes), self.assertRaises(ValueError): status(self.work)

    def test_prompt_only_requires_actual_common_material(self):
        self.init(task='B02')
        prompt = (self.work/'PROMPT.md').read_text()
        self.assertNotIn('task.json', prompt)
        self.assertTrue((self.work/'candidate/PROMPT.md').is_file())

    def test_status_duplicate_keys_rejected(self):
        self.init()
        (self.work/'manifest.json').write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaises(ValueError): status(self.work)

    def test_status_missing_artifacts(self):
        self.init()
        (self.work/'PROMPT.md').unlink()
        self.assertEqual(status(self.work)['integrity'][0]['status'], 'missing')

    def test_relocated_workspace_rejected(self):
        self.init()
        moved = self.base/'moved'
        self.work.rename(moved)
        with self.assertRaises(ValueError): status(moved)

    def test_failure_rolls_back_new_workspace(self):
        with patch('experiment_tools.workspace.engineering.prepare', side_effect=ValueError('fixture failure')):
            with self.assertRaises(ValueError): self.init()
        self.assertFalse(self.work.exists())

    def test_claude_plan(self):
        self.init(provider='claude')
        data = json.loads((self.work/'command-plan.json').read_text())
        self.assertEqual(data['isolation']['sandbox'], 'not_configured_by_planner')
        self.assertFalse(data['real_integration_tested'])

    def test_integration_explicit_identity(self):
        self.assertEqual(self.init(task='S04-spring')['implementation_id'], 'S04-spring')

    def test_git_plan_uses_outer_workspace_only(self):
        self.init()
        steps = json.loads((self.work/'next-steps.json').read_text())
        self.assertEqual(steps[0]['argv'], ['git', '-C', str(self.work), 'init'])
        self.assertTrue(steps[0]['manual_only'])
        self.assertFalse((self.work/'.git').exists())

    def test_missing_candidate_and_baseline_are_visible(self):
        self.init()
        shutil.rmtree(self.work/'candidate')
        shutil.rmtree(self.work/'baseline')
        report = status(self.work)
        missing = {i['path'] for i in report['integrity'] if i['status'].startswith('missing')}
        self.assertEqual(missing, {'baseline/', 'candidate/', 'baseline/PREPARED.json'})

    def test_special_evidence_rejected_without_blocking(self):
        self.init()
        os.mkfifo(self.work/'trace.jsonl')
        with self.assertRaises(ValueError): status(self.work)

    def test_oversized_evidence_rejected(self):
        self.init()
        with (self.work/'trace.jsonl').open('wb') as stream:
            stream.truncate(16*1024*1024+1)
        with self.assertRaises(ValueError): status(self.work)

    def test_init_never_launches_process(self):
        with patch('subprocess.run', side_effect=AssertionError('must not execute')), patch('subprocess.Popen', side_effect=AssertionError('must not execute')):
            self.init()
            status(self.work)

    def test_doctor_never_launches(self):
        with patch('subprocess.run', side_effect=AssertionError('must not execute')), patch('shutil.which', return_value=None):
            result = doctor('codex')
        self.assertIn('codex', result['missing_tools'])
        self.assertEqual(result['credentials'], 'not_read')

    def test_cli_exit_codes_and_json(self):
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main(['init', '--task', 'B01', '--provider', 'codex', '--model', 'test-model',
                         '--cli-version', 'test-version', '--workspace', str(self.work)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['execution_status'], 'not_run')
        with contextlib.redirect_stderr(error):
            code = main(['status', '--workspace', str(self.base/'missing')])
        self.assertEqual(code, 2)


if __name__ == '__main__':
    unittest.main()
