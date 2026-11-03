import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiment_tools import dot_native as dot
from experiment_tools.workspace import write_json
from cli_adapters.common import canonical, sha256

class DotNativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'experiment'
        skills = Path(self.temp.name)/'skills-source'
        hashes = {}
        for stage in dot.STAGES:
            p = skills/'skills'/stage/'SKILL.md'
            p.parent.mkdir(parents=True)
            p.write_text(stage)
            hashes[stage] = sha256(stage.encode())
        self.mock = patch.object(dot, 'SKILL_HASHES', hashes)
        self.mock.start()
        self.addCleanup(self.mock.stop)
        dot.prepare(self.root, skills)
        self.slot = 'B02-r1-no-skill'
        self.obs = {'status':'completed', 'agent_id':'test-agent', 'operator_evidence':'unit fixture only',
                    'final_text':'done', 'elapsed_seconds':None, 'cost_usd':None,
                    'started_at':'2026-11-01T08:00:00Z','finished_at':'2026-11-01T08:01:00Z'}
        dot.begin(self.root,self.slot,'test-agent',self.obs['started_at'])

    def test_missing_retained_and_unknowns_null(self):
        result = dot.display(self.root)
        self.assertEqual(12, len(result['slots']))
        self.assertTrue(all(x['execution_status']=='missing' and x['cost_usd'] is None for x in result['slots']))
        self.assertFalse(result['smoke_included'])

    def test_completed_not_business_success(self):
        result = dot.record(self.root, self.slot, self.obs)
        self.assertEqual('not_evaluated', result['business_status'])
        self.assertEqual('completed', dot.display(self.root)['slots'][0]['execution_status'])
        with self.assertRaises(ValueError): dot.record(self.root, self.slot, self.obs)

    def test_modified_prompt_rejected(self):
        (self.root/'slots'/self.slot/'PROMPT.txt').write_text('changed')
        with self.assertRaises(ValueError): dot.record(self.root, self.slot, self.obs)

    def test_plan_tamper_rejected(self):
        p=self.root/'plan.json'; obj=json.loads(p.read_text()); obj['backend_model']='invented'; write_json(p,obj)
        with self.assertRaises(ValueError): dot.display(self.root)

    def test_control_skill_contamination_rejected(self):
        (self.root/'slots'/self.slot/'workflow').mkdir()
        with self.assertRaises(ValueError): dot.record(self.root, self.slot, self.obs)

    def test_unknown_slot_rejected(self):
        with self.assertRaises(ValueError): dot.record(self.root, 'not-in-plan', self.obs)

    def test_no_evidence_rejected(self):
        self.obs['operator_evidence']=''
        with self.assertRaises(ValueError): dot.record(self.root, self.slot, self.obs)

    def test_negative_or_boolean_metrics_rejected(self):
        for value in (-1, True, 0, 1.5):
            self.obs['cost_usd']=value
            with self.assertRaises(ValueError): dot.record(self.root, self.slot, self.obs)

    def test_report_requires_review(self):
        with self.assertRaises(ValueError): dot.record(self.root, self.slot, self.obs, {'status':'passed'})

    def test_failed_and_cancelled_preserved(self):
        for status, slot in [('failed','B02-r1-no-skill'),('cancelled','B02-r1-workflow')]:
            if slot != self.slot: dot.begin(self.root,slot,'test-agent',self.obs['started_at'])
            dot.record(self.root, slot, dict(self.obs,status=status))
        rows=dot.display(self.root)['slots']
        self.assertEqual(['failed','cancelled'],[r['execution_status'] for r in rows[:2]])

    def test_patch_captures_changes(self):
        (self.root/'slots'/self.slot/'candidate'/'delivery-note.md').write_text('test output')
        result=dot.record(self.root,self.slot,self.obs)
        self.assertIn('+test output',result['patch'])

    def test_synthetic_record_rejected(self):
        dot.record(self.root,self.slot,self.obs)
        path=self.root/'records'/f'{self.slot}.json'
        rec=json.loads(path.read_text());rec['data_class']='synthetic';write_json(path,rec)
        with self.assertRaises(ValueError): dot.display(self.root)

    def test_display_revalidates_metrics_and_business_status(self):
        dot.record(self.root,self.slot,self.obs)
        path=self.root/'records'/f'{self.slot}.json'
        original=json.loads(path.read_text())
        for field,value in [('cost_usd',-10),('cost_usd',True)]:
            rec=json.loads(json.dumps(original));rec['execution'][field]=value;write_json(path,rec)
            with self.assertRaises(ValueError): dot.display(self.root)
        rec=json.loads(json.dumps(original));rec['business_status']='invented-green';write_json(path,rec)
        with self.assertRaises(ValueError): dot.display(self.root)

    def test_preseeded_candidate_start_rejected(self):
        slot='B02-r1-workflow'
        (self.root/'slots'/slot/'candidate'/'answer.txt').write_text('preseeded')
        with self.assertRaises(ValueError): dot.begin(self.root,slot,'new-agent')

    def test_start_order_and_duplicate_rejected(self):
        with self.assertRaises(ValueError): dot.begin(self.root,'S01-r3-workflow','new-agent')
        with self.assertRaises(FileExistsError): dot.begin(self.root,self.slot,'new-agent')

    def test_missing_start_and_wrong_agent_rejected(self):
        with self.assertRaises(FileNotFoundError): dot.record(self.root,'B02-r1-workflow',self.obs)
        with self.assertRaises(ValueError): dot.record(self.root,self.slot,dict(self.obs,agent_id='wrong-agent'))

    def test_minimal_fabricated_report_rejected(self):
        from scripts import engineering
        current=engineering.file_hashes(self.root/'slots'/self.slot/'candidate')
        fake={'schema_version':'engineering-1.0','candidate_files':current,
              'submission_sha256':sha256(json.dumps(current,sort_keys=True).encode()),
              'design_id':'B02','manifest_sha256':sha256((engineering.task_path('B02')/'task.json').read_bytes()),
              'status':'passed','passed':True,'exit_code':0}
        review={'approved_for_local_execution':True,'candidate_files':current,'reviewer':'unit','notes':'unit'}
        with self.assertRaises(ValueError): dot.record(self.root,self.slot,self.obs,fake,review)

    def test_receipt_input_hash_tamper_rejected(self):
        path=self.root/'starts'/f'{self.slot}.json'
        receipt=json.loads(path.read_text());receipt['input_sha256']='0'*64;write_json(path,receipt)
        with self.assertRaises(ValueError): dot.record(self.root,self.slot,self.obs)

if __name__ == '__main__': unittest.main()
