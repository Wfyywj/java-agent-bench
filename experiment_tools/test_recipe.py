"""Synthetic contract tests; no models, subprocesses or candidate execution."""
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from analysis_tools.paired_analysis import validate, ValidationError
from experiment_tools import recipe as r


class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.recipe = self.parent/'recipe.json'
        self.run = self.parent/'run'
        r.write_json(self.recipe, r.example())

    def freeze(self):
        return r.freeze(self.recipe, self.run, True)

    def replay(self):
        self.freeze()
        return r.replay(self.run, True)

    def test_end_to_end_all_slots_and_unknowns(self):
        with patch('subprocess.Popen', side_effect=AssertionError('no process allowed')):
            self.replay()
            result = r.export_analysis(self.run, True)
        self.assertEqual((result['status'], result['records'], result['planned_slots']), ('incomplete', 4, 6))
        envelopes = r.load(self.run/'replay/ledger.json')['slots']
        self.assertEqual([e['state'] for e in envelopes], ['failure', 'success', 'infrastructure_failure', 'cancelled', 'missing', 'failure'])
        self.assertEqual(len({e['source_content_sha256'] for e in envelopes}), 1)
        records = r.load(self.run/'analysis/records.json')
        self.assertTrue(all(e['run_kind'] == 'synthetic_replay' and e['cost_usd'] is None and e['elapsed_seconds'] is None for e in records))
        report = r.load(self.run/'analysis/report.json')
        self.assertEqual(len(report['missing_slots']), 2)
        self.assertFalse(r.load(self.run/'analysis/display.json')['website_import_supported'])

    def test_complete_replay(self):
        recipe = r.example(); recipe['repeats'] = [{'repeat': 1, 'A': 'failure', 'B': 'success'}]
        r.write_json(self.recipe, recipe)
        self.replay()
        self.assertEqual(r.export_analysis(self.run, True)['status'], 'complete')

    def test_explicit_opt_in_and_actual_rejection(self):
        with self.assertRaises(ValueError): r.freeze(self.recipe, self.run)
        recipe = r.example(); recipe['data_class'] = 'actual_agent_trials'; r.write_json(self.recipe, recipe)
        with self.assertRaises(ValueError): self.freeze()
        self.assertFalse(self.run.exists())

    def test_immutable_freeze_replay_analysis(self):
        self.replay()
        with self.assertRaises(ValueError): self.freeze()
        with self.assertRaises(ValueError): r.replay(self.run, True)
        r.export_analysis(self.run, True)
        with self.assertRaises(ValueError): r.export_analysis(self.run, True)

    def test_independent_workspaces_and_mutation_rejection(self):
        self.freeze()
        first = self.run/'slots/repeat-1-A/candidate/PROMPT.md'
        other = self.run/'slots/repeat-1-B/candidate/PROMPT.md'
        baseline = self.run/'slots/repeat-1-A/baseline/PROMPT.md'
        before = other.read_bytes()
        first.write_text('modified')
        self.assertEqual(other.read_bytes(), before)
        self.assertEqual(baseline.read_bytes(), before)
        with self.assertRaises(ValueError): r.replay(self.run, True)

    def test_plan_and_version_tamper(self):
        self.freeze()
        plan = r.load(self.run/'plan.json'); plan['pairs'][0]['manifest_sha256'] = '0'*64
        r.write_json(self.run/'plan.json', plan)
        with self.assertRaises(ValueError): r.replay(self.run, True)

    def test_source_binding_rejects_changed_version(self):
        self.freeze()
        with patch.object(r, 'bindings', return_value={}):
            with self.assertRaises(ValueError): r.replay(self.run, True)

    def test_evidence_tamper(self):
        self.replay()
        (self.run/'replay/repeat-1-A-trace.json').write_text('{"run_kind":"localreference"}')
        with self.assertRaises(ValueError): r.export_analysis(self.run, True)
        self.assertFalse((self.run/'analysis').exists())

    def test_missing_ledger_slot_rejected(self):
        self.replay()
        ledger = r.load(self.run/'replay/ledger.json'); ledger['slots'].pop()
        r.write_json(self.run/'replay/ledger.json', ledger)
        with self.assertRaises(ValueError): r.export_analysis(self.run, True)

    def test_strict_analysis_actual_and_reference_remain_rejected(self):
        self.replay(); r.export_analysis(self.run, True)
        plan = r.load(self.run/'plan.json'); records = r.load(self.run/'analysis/records.json')
        with self.assertRaises(ValueError): validate(plan, records)
        for kind in ('selfcheck', 'localreference', 'reference'):
            modified = copy.deepcopy(records); modified[0]['run_kind'] = kind
            with self.assertRaises(ValueError): validate(plan, modified, True)
        plan['data_class'] = 'actual_agent_trials'
        for record in records: record['data_class'] = 'actual_agent_trials'
        with self.assertRaises(ValueError): validate(plan, records, True)

    def test_hash_semantics_preparation_metadata(self):
        self.freeze()
        slot = self.run/'slots/repeat-1-A'
        source = r.source_hash(slot); artifact = r.snapshot(slot)[0]['source_sha256']
        (slot/'candidate/PREPARED.json').write_text('{"prepared_at":"different"}')
        self.assertEqual(source, r.source_hash(slot))
        self.assertNotEqual(artifact, r.snapshot(slot)[0]['source_sha256'])

    def test_json_schema_preserves_resource_and_synthetic_constraints(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('optional JSON Schema validator not installed')
        import json
        self.replay(); r.export_analysis(self.run, True)
        schema = json.loads((r.ROOT/'analysis_tools/input.schema.json').read_text())
        schema.pop('oneOf', None)
        schema['$ref'] = '#/$defs/record'
        record = r.load(self.run/'analysis/records.json')[0]
        jsonschema.validate(record, schema)
        for field, value in [('cost_unknown_reason', None), ('elapsed_unknown_reason', None),
                             ('data_class', 'actual_agent_trials')]:
            changed = copy.deepcopy(record); changed[field] = value
            with self.assertRaises(jsonschema.ValidationError): jsonschema.validate(changed, schema)
        bridge = json.loads((r.ROOT/'experiment_tools/recipe.schema.json').read_text())
        # Inline the shared definition for a network-free schema test.
        for definition in ('recipe', 'envelope'):
            def inline(value):
                if isinstance(value, dict):
                    if value.get('$ref') == '../analysis_tools/input.schema.json#/$defs/metadata':
                        return schema['$defs']['metadata']
                    return {k:inline(v) for k,v in value.items()}
                if isinstance(value, list): return [inline(v) for v in value]
                return value
            bridge['$defs'][definition] = inline(bridge['$defs'][definition])
        jsonschema.validate(r.example(), bridge)
        for envelope in r.load(self.run/'replay/ledger.json')['slots']:
            jsonschema.validate(envelope, bridge)

    def test_unknown_fields_duplicate_json_symlink(self):
        recipe = r.example(); recipe['surprise'] = True; r.write_json(self.recipe, recipe)
        with self.assertRaises(ValueError): self.freeze()
        self.recipe.write_text('{"task":"B01","task":"B02"}')
        with self.assertRaises(ValueError): self.freeze()
        link = self.parent/'link'; link.symlink_to(self.recipe)
        with self.assertRaises(ValueError): r.freeze(link, self.run, True)

    def test_directed_synthetic_impersonation_repro_blocks(self):
        repo = Path(__file__).resolve().parents[1]
        script = repo / 'docs/acceptance/fixtures/directed-counterexamples/synthetic-impersonation/repro.py'
        run = subprocess.run([sys.executable, str(script)], cwd=repo, capture_output=True, text=True, timeout=120)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn('verdict: blocks', run.stdout)
        self.assertIn('website_import_supported=false', run.stdout)
        self.assertIn('actual_recipe_exit: 1', run.stdout)
        self.assertIn('evidence_rejected: True', run.stdout)
        self.assertNotIn('verdict: still-fails', run.stdout)


if __name__ == '__main__':
    unittest.main()
