"""Exploratory, operator-orchestrated dot experiments; not a CLI or security sandbox."""
import argparse
import difflib
import json
import math
from pathlib import Path
import shutil
import sys
import re
from datetime import datetime, timezone

from cli_adapters.common import canonical, read_regular, sha256, strict_json
from experiment_tools.workspace import write_json
from experiment_tools.pilot import STAGES, SKILL_HASHES, SKILL_REVISION, source_bindings, require
from scripts import engineering

SCHEMA = 'dot-native-results-1.0'
LABEL = 'actual_dot_exploratory'
COMMON = '''Complete the task in candidate/PROMPT.md using only the supplied task materials.
Read and modify only candidate/; workflow/ may be read only when supplied. Do not read sibling directories,
other trials, benchmark repository, reference solutions, verifier, mutants, or external solutions.
Use shell/file tools only within this slot. No network, connected apps, other agents, external skills,
credentials, package installation, publishing, persistent memory or cross-trial learning.
You may compile and run your own regression tests using installed Java 21 and Python 3.
Do not run unavailable benchmark selfchecks or request their results. Preserve public input files and contract.
If genuine clarification is necessary, record it and stop. Deliver locally with changed files,
tests run and unverified items. This public exploratory experiment has instruction-only separation,
not a security sandbox. No workflow skill is supplied unless workflow/ exists.
'''
WORKFLOW = '''Follow the six supplied stages in order: clarify-task, plain-plan, implement-slice,
verify-change, review-change, deliver-change. Read workflow/<stage>.md. Record each stage's concrete
output and evidence in candidate/workflow-trace.md, including changes resulting from review.
Do not claim a stage was performed merely because its instructions were read. Delivery is local-only;
do not invoke learn-from-task or retain memory across trials.
'''


def now():
    return datetime.now(timezone.utc).isoformat()


def digest_files(path):
    return sha256(canonical(engineering.file_hashes(path)))


def load_plan(root):
    plan = strict_json(read_regular(root/'plan.json'))
    require(plan['schema_version'] == 'dot-native-plan-1.0', 'wrong plan schema')
    require(sha256(canonical(plan)) == read_regular(root/'plan.sha256').decode().strip(), 'plan changed')
    require(plan['source_bindings'] == source_bindings(), 'benchmark or runner changed after freeze')
    return plan


def prepare(root, skill_root):
    root = root.resolve()
    require(not root.exists(), 'destination exists; never overwrite an experiment')
    require(not root.is_relative_to(engineering.ROOT), 'use destination outside repository')
    texts = {s: read_regular(skill_root/'skills'/s/'SKILL.md') for s in STAGES}
    require({s: sha256(v) for s, v in texts.items()} == SKILL_HASHES, 'skill revision mismatch')
    root.mkdir(parents=True)
    inputs = {}
    for task in ('B02', 'S01'):
        engineering.prepare(task, root/'inputs'/task)
        inputs[task] = digest_files(root/'inputs'/task)
    rows = []
    for task in ('B02', 'S01'):
        for repeat in (1, 2, 3):
            arms = ('no-skill', 'workflow') if repeat % 2 else ('workflow', 'no-skill')
            for arm in arms:
                ident = f'{task}-r{repeat}-{arm}'
                slot = root/'slots'/ident
                shutil.copytree(root/'inputs'/task, slot/'candidate')
                prompt = COMMON
                if arm == 'workflow':
                    prompt += WORKFLOW
                    (slot/'workflow').mkdir()
                    for stage, data in texts.items():
                        (slot/'workflow'/f'{stage}.md').write_bytes(data)
                (slot/'PROMPT.txt').write_text(prompt)
                rows.append({'slot_id': ident, 'task': task, 'arm': arm, 'repeat': repeat,
                             'input_sha256': inputs[task], 'prompt_sha256': sha256(prompt.encode())})
    plan = {'schema_version': 'dot-native-plan-1.0', 'created_at': now(), 'data_class': LABEL,
            'harness': 'dot-native fresh no-history agent, operator orchestrated',
            'execution_mode': 'dot_native', 'isolation': 'shared_filesystem_soft_boundary',
            'backend_model': None, 'backend_version': None, 'cost_usd': None,
            'source_bindings': source_bindings(), 'workflow_revision': SKILL_REVISION,
            'workflow_hashes': SKILL_HASHES, 'slots': rows,
            'limitations': ['shared filesystem; instruction-only separation, not secure isolation',
                'public development tasks; possible training contamination',
                'backend identity, billing and full raw provider trace unavailable',
                'no enforceable per-agent token/cost limit; operator cancellation only',
                'fresh conversation does not prove identical model routing',
                'three repeats per arm are exploratory, not a ranking or causal proof'],
            'policy': {'retries': 'none; keep all slots', 'smoke': 'separate preflight, excluded',
                       'attempt_wall_limit_seconds': 900, 'timeout_enforcement': 'parent-observed best effort cancellation; no hard runtime limit',
                       'model_routing': 'fresh no-history agents, same inherited default model and effort, no overrides',
                       'usage_and_cost': 'unavailable; null, never zero',
                       'result_authority': 'operator-observed, unsigned; hashes are not authentication',
                       'workflow': 'provided context plus recorded stage artifacts; audit adherence separately'}}
    write_json(root/'plan.json', plan)
    (root/'plan.sha256').write_text(sha256(canonical(plan))+'\n')
    return plan


def metric(value, label):
    require(value is None or (isinstance(value, (float, int)) and not isinstance(value, bool)
                             and math.isfinite(value) and value >= 0), 'invalid '+label)


def timestamp(value):
    require(isinstance(value, str), 'timestamp required')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None, 'timezone required')
    return parsed


def validate_observation(observation):
    require(isinstance(observation, dict), 'observation must be object')
    require(observation.get('status') in ('completed', 'failed', 'cancelled', 'timeout'), 'invalid execution status')
    for key in ('operator_evidence', 'agent_id'):
        require(isinstance(observation.get(key), str) and bool(observation[key].strip()), key+' required')
    require(isinstance(observation.get('final_text'), str), 'final text required')
    metric(observation.get('elapsed_seconds'), 'elapsed_seconds')
    require(observation.get('cost_usd') is None, 'cost unavailable in this profile; must remain null')
    require(timestamp(observation.get('finished_at')) >= timestamp(observation.get('started_at')), 'inverted time')


def begin(root, slot_id, agent_id, started_at=None):
    plan = load_plan(root)
    rows = [s for s in plan['slots'] if s['slot_id'] == slot_id]
    require(len(rows) == 1, 'unknown slot')
    row = rows[0]; slot = root/'slots'/slot_id
    for prior in plan['slots'][:plan['slots'].index(row)]:
        require((root/'starts'/f"{prior['slot_id']}.json").is_file(), 'start in frozen plan order')
    require(digest_files(slot/'candidate') == row['input_sha256'], 'candidate changed before start')
    if row['arm'] == 'workflow':
        require({s: sha256(read_regular(slot/'workflow'/f'{s}.md')) for s in STAGES} == SKILL_HASHES, 'workflow changed before start')
    else:
        require(not (slot/'workflow').exists(), 'control contaminated before start')
    require(sha256(read_regular(slot/'PROMPT.txt')) == row['prompt_sha256'], 'prompt changed before start')
    require(isinstance(agent_id,str) and bool(agent_id.strip()), 'agent_id required')
    receipt = dict(row, plan_sha256=sha256(canonical(plan)), agent_id=agent_id,
                   started_at=started_at or now(), authority='operator-observed launch receipt')
    timestamp(receipt['started_at'])
    path=root/'starts'/f'{slot_id}.json';path.parent.mkdir(exist_ok=True)
    with path.open('x') as stream: json.dump(receipt, stream, sort_keys=True)
    return receipt


def validate_report(report, review, current, task):
    require(isinstance(review,dict) and review.get('approved_for_local_execution') is True, 'explicit source review required')
    require(review.get('candidate_files') == current and bool(review.get('reviewer')) and bool(review.get('notes')),
            'review must bind exact candidate and include reviewer/notes')
    require(isinstance(report,dict) and report.get('schema_version') == 'engineering-1.0', 'not an engineering report')
    require(report.get('candidate_files') == current, 'report candidate differs')
    require(report.get('submission_sha256') == sha256(json.dumps(current,sort_keys=True).encode()), 'report digest differs')
    require(report.get('design_id') == task and report.get('implementation_id') == task+'-slice', 'report task differs')
    require(report.get('manifest_sha256') == sha256(read_regular(engineering.task_path(task)/'task.json')), 'manifest differs')
    require(report.get('dataset') == 'public-dev-slices', 'report dataset differs')
    timestamp(report.get('timestamp_utc'));metric(report.get('elapsed_seconds'), 'verifier elapsed_seconds')
    environment=report.get('environment');provenance=report.get('evaluator_provenance')
    require(isinstance(environment,dict) and all(isinstance(environment.get(k),str) and environment[k] for k in ('java','python','platform')), 'environment missing')
    require(isinstance(provenance,dict) and isinstance(provenance.get('git_head'),str)
            and re.fullmatch('[a-f0-9]{40}',provenance['git_head'])
            and type(provenance.get('working_tree_dirty')) is bool, 'evaluator provenance missing')
    status=report.get('status')
    require(status in ('passed','failed','timeout','output_limit','invalid_report'), 'invalid verifier status')
    require(type(report.get('passed')) is bool and report['passed'] == (status=='passed'), 'inconsistent verifier status')
    require(type(report.get('exit_code')) is int, 'exit code missing')
    require(isinstance(report.get('log'),str), 'verifier log missing')
    nested=report.get('report')
    if status in ('timeout','output_limit','invalid_report'):
        require(report['passed'] is False, 'infrastructure outcome cannot pass')
        return
    require(isinstance(nested,dict) and strict_json(report['log'].encode()) == nested, 'nested report/log mismatch')
    require(type(nested.get('passed')) is bool and nested['passed']==report['passed'], 'nested outcome mismatch')
    require((report['exit_code']==0) == report['passed'], 'exit/outcome mismatch')
    if task=='B02':
        require(nested.get('task_id') == task, 'nested task mismatch')
        if nested.get('status')=='input_or_infrastructure_error':
            require(not report['passed'] and bool(nested.get('error')), 'bad infrastructure failure')
            return
        checks=nested.get('checks')
        require(isinstance(checks,dict), 'checks missing')
        if nested.get('status')=='build_failed':
            require(not report['passed'] and not checks and isinstance(nested.get('compile_log'),str), 'bad build failure')
            return
        if nested.get('status')=='input_or_infrastructure_error':
            require(not report['passed'] and bool(nested.get('error')), 'bad infrastructure failure')
            return
        expected={'B02-A01_replay_restart','B02-A02_payload_conflicts','B02-A04_tenant_lifecycle',
                  'B02-A04_equipment_binding_false','B02-A04_equipment_binding_true',
                  'B02-A05_concurrent_http','B02-A05_damaged_review'} | {f'B02-A03_rollback_write_{n}' for n in (1,2,3)}
        require(set(checks)==expected, 'incomplete B02 checks')
        require(all(isinstance(v,str) and (v=='PASS' or v.startswith(('FAIL: ','ERROR: '))) for v in checks.values()), 'invalid check value')
        require(all(v=='PASS' for v in checks.values()) == report['passed'], 'check/outcome mismatch')
        require(nested.get('status')==('passed' if report['passed'] else 'verification_failed'), 'nested status mismatch')
    else:
        require(nested.get('id')==task and type(nested.get('compiled')) is bool, 'nested S01 identity missing')
        cases=strict_json(read_regular(engineering.task_path(task)/'fixtures/cases.json'))
        checks=nested.get('checks'); require(isinstance(checks,list), 'checks missing')
        if nested.get('error'):
            require(not report['passed'], 'error cannot pass');return
        require(nested['compiled'] and len(checks)==len(cases), 'incomplete S01 checks')
        outcomes=[]
        for check, case in zip(checks,cases):
            require(check.get('name')==case['name'] and check.get('acceptance')==case['acceptance'], 'S01 check identity mismatch')
            steps=check.get('steps');require(isinstance(steps,list) and 1<=len(steps)<=len(case['steps']), 'missing S01 steps')
            outcomes_for_case=[]
            for step, expected in zip(steps,case['steps']):
                require(step.get('args')==expected['args'], 'S01 args mismatch')
                if step.get('error'):
                    require(step.get('passed') is False, 'error cannot pass');outcomes_for_case.append(False);continue
                require(step.get('expected')==expected['expected'] and 'actual' in step, 'missing comparison')
                actual=step['actual'];target=expected['expected'];ok=actual in target if isinstance(target,list) else actual==target
                require(step.get('passed') is ok, 'S01 step outcome mismatch');outcomes_for_case.append(ok)
            passed=all(outcomes_for_case) and len(steps)==len(case['steps'])
            require(check.get('passed') is passed, 'S01 check outcome mismatch');outcomes.append(passed)
        require(all(outcomes)==report['passed'], 'S01 outcome mismatch')


def validate_record(rec, plan, slot):
    require(rec.get('schema_version')==SCHEMA and rec.get('data_class')==LABEL, 'non-actual record rejected')
    require(rec.get('plan_sha256')==sha256(canonical(plan)), 'record plan mismatch')
    require(all(rec.get(k)==v for k,v in slot.items()), 'record identity mismatch')
    validate_observation(rec.get('execution'))
    current=rec.get('candidate_files')
    require(isinstance(current,dict) and bool(current) and all(isinstance(k,str) and isinstance(v,str) and re.fullmatch('[a-f0-9]{64}',v) for k,v in current.items()), 'candidate hashes invalid')
    require(rec.get('candidate_sha256')==sha256(canonical(current)), 'candidate hash mismatch')
    report=rec.get('evaluation')
    if report is None:
        require(rec.get('business_status')=='not_evaluated', 'business status needs report')
    else:
        validate_report(report,rec.get('source_review'),current,slot['task'])
        require(rec.get('business_status')==report['status'], 'business/report mismatch')
    receipt=rec.get('start_receipt')
    require(isinstance(receipt,dict) and receipt.get('plan_sha256')==rec['plan_sha256']
            and all(receipt.get(k)==v for k,v in slot.items()) and receipt.get('agent_id')==rec['execution']['agent_id']
            and receipt.get('started_at')==rec['execution']['started_at'], 'start receipt mismatch')


def record(root, slot_id, observation, report=None, review=None):
    plan = load_plan(root)
    rows = [s for s in plan['slots'] if s['slot_id'] == slot_id]
    require(len(rows) == 1, 'unknown slot')
    row = rows[0]
    slot = root/'slots'/slot_id
    out = root/'records'/f'{slot_id}.json'
    require(not out.exists(), 'slot already recorded; append a new experiment, never replace')
    require(digest_files(root/'inputs'/row['task']) == row['input_sha256'], 'input changed')
    require(sha256(read_regular(slot/'PROMPT.txt')) == row['prompt_sha256'], 'prompt changed')
    if row['arm'] == 'workflow':
        require({s: sha256(read_regular(slot/'workflow'/f'{s}.md')) for s in STAGES} == SKILL_HASHES,
                'workflow changed')
    else:
        require(not (slot/'workflow').exists(), 'control contaminated with workflow directory')
    validate_observation(observation)
    start_receipt = strict_json(read_regular(root/'starts'/f'{slot_id}.json'))
    candidate = slot/'candidate'
    current = engineering.file_hashes(candidate)
    original = engineering.file_hashes(root/'inputs'/row['task'])
    patch = []
    for name in sorted(set(current) | set(original)):
        if current.get(name) == original.get(name):
            continue
        a = root/'inputs'/row['task']/name
        b = candidate/name
        old = a.read_text(errors='replace').splitlines(True) if a.exists() else []
        new = b.read_text(errors='replace').splitlines(True) if b.exists() else []
        patch.extend(difflib.unified_diff(old, new, fromfile='a/'+name, tofile='b/'+name))
    business = 'not_evaluated'
    if report is not None:
        validate_report(report, review, current, row['task'])
        business = report['status']
    result = dict(row, schema_version=SCHEMA, data_class=LABEL, recorded_at=now(),
                  plan_sha256=sha256(canonical(plan)), candidate_files=current,
                  candidate_sha256=sha256(canonical(current)), execution=observation,
                  business_status=business, evaluation=report, source_review=review, start_receipt=start_receipt,
                  workflow_trace_present=(candidate/'workflow-trace.md').is_file(),
                  workflow_adherence='not_independently_audited',
                  patch=''.join(patch), authenticity='unsigned operator evidence; not provider attestation')
    validate_record(result, plan, row)
    out.parent.mkdir(exist_ok=True)
    with out.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)+'\n')
    return result


def display(root):
    plan = load_plan(root)
    rows = []
    for slot in plan['slots']:
        path = root/'records'/f"{slot['slot_id']}.json"
        if path.exists():
            rec = strict_json(read_regular(path))
            validate_record(rec, plan, slot)
            rows.append(dict(slot, execution_status=rec['execution']['status'], business_status=rec['business_status'],
                elapsed_seconds=rec['execution'].get('elapsed_seconds'), cost_usd=rec['execution'].get('cost_usd'),
                evidence_path=f"records/{slot['slot_id']}.json", evidence_sha256=sha256(read_regular(path))))
        else:
            rows.append(dict(slot, execution_status='missing', business_status='not_evaluated',
                             elapsed_seconds=None, cost_usd=None, evidence_path=None, evidence_sha256=None))
    return {'schema_version': SCHEMA, 'data_class': LABEL, 'plan_sha256': sha256(canonical(plan)),
            'backend_model': None, 'backend_version': None, 'limitations': plan['limitations'],
            'smoke_included': False, 'slots': rows}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=('prepare', 'begin', 'record', 'display'))
    ap.add_argument('--root', required=True, type=Path)
    ap.add_argument('--skill-root', type=Path)
    ap.add_argument('--slot')
    ap.add_argument('--agent-id')
    ap.add_argument('--started-at')
    ap.add_argument('--observation', type=Path)
    ap.add_argument('--report', type=Path)
    ap.add_argument('--review', type=Path)
    args = ap.parse_args()
    try:
        if args.command == 'prepare':
            require(args.skill_root is not None, '--skill-root required')
            result = prepare(args.root, args.skill_root)
        elif args.command == 'begin':
            result = begin(args.root, args.slot, args.agent_id, args.started_at)
        elif args.command == 'record':
            require(args.observation is not None and args.slot, '--observation and --slot required')
            result = record(args.root, args.slot, strict_json(read_regular(args.observation)),
                            strict_json(read_regular(args.report)) if args.report else None,
                            strict_json(read_regular(args.review)) if args.review else None)
        else:
            result = display(args.root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
