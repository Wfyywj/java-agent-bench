import importlib.util,json,tempfile,unittest
from pathlib import Path
SPEC=importlib.util.spec_from_file_location('engineering_launcher',Path(__file__).resolve().parents[1]/'scripts/engineering.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)
class LauncherTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'repo';self.old=M.ROOT;M.ROOT=self.root
  self.t=self.root/'engineering/bronze/B01';(self.t/'baseline/src').mkdir(parents=True)
  (self.t/'baseline/src/Main.java').write_text('class Main {}')
  (self.t/'task.json').write_text('{"version":"test"}')
  (self.t/'agent-files.json').write_text(json.dumps({'files':[{'source':'baseline/src/Main.java','target':'src/Main.java'}]}))
  self.dest=Path(self.temp.name)/'work'
 def tearDown(self):M.ROOT=self.old;self.temp.cleanup()
 def test_prepare_only_allowlist(self):
  (self.t/'reference').mkdir();(self.t/'reference/secret.txt').write_text('answer')
  r=M.prepare('B01',self.dest);self.assertFalse(r['executed']);self.assertTrue((self.dest/'src/Main.java').exists());self.assertFalse((self.dest/'reference').exists())
 def test_no_overwrite(self):
  M.prepare('B01',self.dest)
  with self.assertRaises(ValueError):M.prepare('B01',self.dest)
 def test_path_escape(self):
  for p in ('../x','/tmp/x','a/../../x','a\\b'):
   with self.assertRaises(ValueError):M.safe_relative(p)
 def test_reject_inside_repo(self):
  with self.assertRaises(ValueError):M.prepare('B01',self.root/'work')
 def test_reject_source_symlink(self):
  (self.t/'baseline/src/Link.java').symlink_to(self.t/'baseline/src/Main.java')
  with self.assertRaises(ValueError):M.safe_file(self.t,'baseline/src/Link.java')
 def test_reject_reference_whitelist(self):
  (self.t/'reference').mkdir();(self.t/'reference/Solution.java').write_text('secret')
  (self.t/'agent-files.json').write_text(json.dumps({'files':[{'source':'reference/Solution.java','target':'src/Main.java'}]}))
  with self.assertRaises(ValueError):M.prepare('B01',self.dest)
 def test_gate_before_execution(self):
  with self.assertRaises(ValueError):M.evaluate('B01',self.dest,None,1,False)
 def test_hashes_stable(self):
  M.prepare('B01',self.dest);self.assertEqual(M.file_hashes(self.dest),M.file_hashes(self.dest))
 def test_invalid_id(self):
  with self.assertRaises(ValueError):M.task_path('../../bad')
 def test_evaluation_json_wrapper(self):
  M.prepare('B01',self.dest);(self.t/'run_selfcheck.py').write_text('import json; print(json.dumps({"assertions": [True]}))')
  r=M.evaluate('B01',self.dest,None,5,True);self.assertEqual(r['status'],'passed');self.assertEqual(len(r['submission_sha256']),64);self.assertIsNone(r['model'])
 def test_invalid_report_not_pass(self):
  M.prepare('B01',self.dest);(self.t/'run_selfcheck.py').write_text('print("not json")')
  r=M.evaluate('B01',self.dest,None,5,True);self.assertEqual(r['status'],'invalid_report');self.assertFalse(r['passed'])
if __name__=='__main__':unittest.main()
