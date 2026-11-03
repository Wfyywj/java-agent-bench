"""Offline packet contracts; fixtures do not represent model trials."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from cli_adapters.collection import snapshot
from cli_adapters.common import sha256
from experiment_tools.pilot import STAGES, prepare, verify


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skills = self.root/'skills-source'
        for stage in STAGES:
            file = self.skills/'skills'/stage/'SKILL.md'
            file.parent.mkdir(parents=True)
            file.write_text('Fixture instruction: ' + stage)
        self.packet = self.root/'packet'
        patcher = patch('experiment_tools.pilot.SKILL_HASHES',
                        {s: sha256(('Fixture instruction: ' + s).encode()) for s in STAGES})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_thirteen_independent_slots_and_no_execution(self):
        with patch('subprocess.Popen', side_effect=AssertionError('no execution')):
            result = prepare(self.skills, self.packet)
        self.assertFalse(result['launch_supported'])
        self.assertEqual(verify(self.packet)['integrity'], 'unchanged')
        manifest = json.loads((self.packet/'manifest.json').read_text())
        self.assertEqual(len(manifest['slots']), 13)
        self.assertEqual(sum(s['phase'] == 'comparison' for s in manifest['slots']), 12)
        self.assertEqual([s['arm'] for s in manifest['slots'][3:5]], ['workflow', 'no-skill'])
        for row in manifest['slots']:
            slot = self.packet/'slots'/row['slot_id']
            self.assertEqual(snapshot(slot/'candidate')[0], manifest['inputs'][row['task']])
            self.assertEqual((slot/'workflow').exists(), row['arm'] == 'workflow')
            self.assertIsNone(row['cost_usd'])
            self.assertEqual(row['state'], 'not_run')
            self.assertFalse((slot/'candidate/reference').exists())
            candidate_file = slot/'candidate/PROMPT.md'
            self.assertNotEqual(candidate_file.stat().st_ino,
                                (self.packet/'inputs'/row['task']/'PROMPT.md').stat().st_ino)
        self.assertIsNone(manifest['model'])

    def test_changed_skill_rejected(self):
        (self.skills/'skills'/STAGES[0]/'SKILL.md').write_text('changed')
        with self.assertRaises(ValueError): prepare(self.skills, self.packet)
        self.assertFalse(self.packet.exists())

    def test_no_overwrite(self):
        prepare(self.skills, self.packet)
        with self.assertRaises(ValueError): prepare(self.skills, self.packet)
        self.assertEqual(verify(self.packet)['integrity'], 'unchanged')

    def test_detects_edit_extra_missing(self):
        for mode in ('edit', 'extra', 'missing'):
            with self.subTest(mode=mode):
                packet = self.root/mode
                prepare(self.skills, packet)
                file = packet/'README.md'
                if mode == 'edit': file.write_text('tamper')
                elif mode == 'missing': file.unlink()
                else: (packet/'extra').write_text('unexpected')
                with self.assertRaises(ValueError): verify(packet)

    def test_rejects_symlinks_and_missing_skills(self):
        file = self.skills/'skills'/STAGES[0]/'SKILL.md'
        file.unlink()
        with self.assertRaises(OSError): prepare(self.skills, self.packet)
        file.symlink_to(self.skills/'skills'/STAGES[1]/'SKILL.md')
        with self.assertRaises(ValueError): prepare(self.skills, self.packet)
        self.assertFalse(self.packet.exists())

    def test_failure_cleans_partial_packet(self):
        with patch('experiment_tools.pilot.shutil.copytree', side_effect=OSError('fixture failure')):
            with self.assertRaises(OSError): prepare(self.skills, self.packet)
        self.assertFalse(self.packet.exists())

    def test_does_not_copy_unrelated_skill_code(self):
        (self.skills/'run.sh').write_text('exit 1')
        prepare(self.skills, self.packet)
        paths = snapshot(self.packet)[1]
        self.assertFalse(any('run.sh' in path or 'learn-from-task' in path for path in paths))


if __name__ == '__main__':
    unittest.main()
