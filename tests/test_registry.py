import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RegistryTests(unittest.TestCase):
 def test_catalog_and_slice_identity(self):
  tasks=json.loads((ROOT/'catalog/tasks.json').read_text());self.assertEqual(len(tasks),25);self.assertEqual(len({x['id'] for x in tasks}),25)
  for tier in ['bronze','silver','gold','diamond','king']:self.assertEqual(sum(t['tier']==tier for t in tasks),5)
  for task in tasks:
   self.assertEqual(task['status'],'design_only');self.assertGreaterEqual(len(task['acceptance']),5);self.assertEqual(sum(x['weight'] for x in task['rubric']),100)
 def test_all_25_slice_whitelists(self):
  count=0
  for tier in ['bronze','silver','gold','diamond','king']:
   for folder in sorted((ROOT/'engineering'/tier).glob('[BSGDK]0[1-5]')):
    manifest=json.loads((folder/'agent-files.json').read_text());self.assertEqual(manifest['schema_version'],1);targets=set()
    for item in manifest['files']:
     source,target=Path(item['source']),Path(item['target']);self.assertFalse(source.is_absolute());self.assertFalse(target.is_absolute());self.assertNotIn('..',source.parts);self.assertNotIn('..',target.parts);self.assertNotIn(str(target),targets);targets.add(str(target));self.assertTrue((folder/source).is_file(),str(folder/source));self.assertFalse((folder/source).is_symlink());self.assertFalse(set(source.parts)&{'reference','verifier','mutants','oracle','evidence'},str(source))
    self.assertTrue((folder/'run_selfcheck.py').is_file());count+=1
  self.assertEqual(count,25)
 def test_published_catalog_matches_source(self):
  self.assertEqual(json.loads((ROOT/'catalog/tasks.json').read_text()),json.loads((ROOT/'dist/tasks.json').read_text()))
if __name__=='__main__':unittest.main()
