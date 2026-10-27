"""Shared honest scope fields for the M1 wave-A task manifests."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = (
    'engineering/bronze/B02/task.json',
    'engineering/silver/S01/task.json',
    'engineering/silver/S04/task.json',
    'engineering/integration/S04-spring/task.json',
    'engineering/gold/G01/task.json',
    'engineering/gold/G05/task.json',
)
SELFCHECKS = {
    'B02': ('entrypoint', 'python3 run_selfcheck.py'),
    'S01': ('selfcheck_command', 'python3 run_selfcheck.py'),
    'S04': ('selfcheck_command', 'python3 run_selfcheck.py'),
    'S04-spring': ('selfcheck_command', 'python3 run_selfcheck.py'),
    'G01': ('command', 'python run.py reference; python selfcheck.py'),
    'G05': ('command', 'python selfcheck.py --write-evidence'),
}


def gaps_of(document):
    gaps = document['not_implemented_or_unmeasured']
    if isinstance(gaps, str):
        return [gaps]
    return gaps


class M1ScopeSchemaTests(unittest.TestCase):
    def test_six_manifests_share_honest_scope_fields(self):
        for relative in MANIFESTS:
            with self.subTest(path=relative):
                document = json.loads((ROOT / relative).read_text())
                self.assertEqual(document['id'], Path(relative).parent.name)
                status = document['implementation_status']
                self.assertIsInstance(status, str)
                self.assertTrue(status.strip())
                self.assertNotIn(status, {'gates_green', 'ready', 'full_catalog_ready', 'design_only'})
                if 'status' in document:
                    self.assertEqual(document['status'], status)
                self.assertIsInstance(document['implemented_scope'], str)
                self.assertTrue(document['implemented_scope'].strip())
                gaps = gaps_of(document)
                self.assertIsInstance(gaps, list)
                self.assertTrue(gaps)
                self.assertTrue(all(isinstance(item, str) and item.strip() for item in gaps))
                self.assertIs(document['full_catalog_ready'], False)
                mutants = document['mutants']
                self.assertIsInstance(mutants, list)
                self.assertTrue(mutants)
                self.assertTrue(all(isinstance(item, str) and item.strip() for item in mutants))
                variants = document.get('variants')
                if isinstance(variants, dict) and isinstance(variants.get('mutants'), list):
                    self.assertEqual(mutants, variants['mutants'])
                if isinstance(variants, list):
                    named = [item for item in variants if isinstance(item, str) and item.startswith('mutant_')]
                    if named:
                        self.assertEqual(mutants, named)
                legacy = document.get('not_implemented')
                if isinstance(legacy, list):
                    self.assertEqual(gaps, legacy)
                excluded = document.get('excluded')
                if isinstance(excluded, list):
                    self.assertTrue(set(excluded) <= set(gaps))
                for legacy_gaps in ('limits', 'limitations'):
                    listed = document.get(legacy_gaps)
                    if isinstance(listed, list) and listed and isinstance(listed[0], str):
                        self.assertTrue(set(listed) <= set(gaps))
                if 'mutant_count' in document:
                    self.assertEqual(document['mutant_count'], len(mutants))
                field, command = SELFCHECKS[document['id']]
                self.assertEqual(document[field], command)


if __name__ == '__main__':
    unittest.main()
