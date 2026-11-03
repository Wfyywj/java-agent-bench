"""Prepare, but never launch, the bounded B02/S01 workflow pilot."""
import argparse
import json
import shutil
import sys

from cli_adapters.common import AdapterError, canonical, read_regular, sha256, strict_json
from cli_adapters.collection import snapshot
from experiment_tools.workspace import ROOT, location, task_identity, write_json
from scripts import engineering

STAGES = ('clarify-task', 'plain-plan', 'implement-slice', 'verify-change', 'review-change', 'deliver-change')
SKILL_REVISION = '80e15acdf61d2cecf1ff79e9088a8149e64ffc1a'
SKILL_HASHES = dict(zip(STAGES, (
    'c9d66842ebea7594a917aee1df1cf7a252a0e9f8a6f4ecf0b7a7f05ee9dcc59d',
    '428623d496f0fd82664880adc4eaa181879a59bcfb51bc5f0e8cfbf35a3f76a4',
    '4e126a93d6ce71eb9963e8c7a982b0ca19d33389911651a2d0f560863d6808a6',
    '26affa7915909758d7c38d59cb809b73c10b96aa680856b81a406d8edea311a3',
    '18243d6c12322ec21f9c87230db6d275e527ff9ca2b2949949120bf9bf35c135',
    '4cbb6241746d09c2dda6f26a3523ab92a00f8af8a6e5bd2a42e86b52346d29d4',
)))
LABEL = 'offline_pilot_preparation_not_model_results'
COMMON_PROMPT = '''Complete the task in candidate/PROMPT.md using the supplied task materials.
Follow any additional instructions below; use no external task solutions.
Modify only candidate/. Do not consult benchmark reference/verifier/mutants or other trials.
This is a public development task, not a hidden evaluation. Do not publish, push, open PRs,
install dependencies, access credentials, or change external state. Deliver locally.
If clarification is necessary, record the question and stop; do not invent an answer.
'''
BLOCKERS = [
    'Exact Codex model and CLI version, auth route, and model configuration not frozen',
    'Owner-approved smoke spending cap and enforceable time/token/cost policy not frozen',
    'Disposable agent isolation and separate verifier isolation not established',
    'User/project/global skills, MCP, tools, network and configuration contamination not audited',
    'Real process supervision, cancellation evidence, raw trace capture and billing capture not implemented',
    'Independent candidate evaluation and authenticated real-result import not implemented',
    'Smoke must finish and be reviewed before authorizing the twelve comparison slots',
]


def require(condition, message):
    if not condition:
        raise AdapterError(message)


def source_bindings():
    """Content identity, not an assertion that these bytes are a clean Git commit."""
    files = {}
    for task in ('B02', 'S01'):
        directory = task_identity(task)[2]
        for relative, data in snapshot(directory)[1].items():
            if '__pycache__' not in relative.split('/') and not relative.endswith('.pyc'):
                files[str(directory.relative_to(ROOT)/relative)] = sha256(data)
    for folder in ('scripts', 'experiment_tools', 'cli_adapters', 'engineering/silver'):
        for path in sorted((ROOT/folder).glob('*.py')):
            files[str(path.relative_to(ROOT))] = sha256(read_regular(path))
    return files


def prepare(skill_root, destination):
    skills = location(skill_root)
    target = location(destination)
    require(not target.exists(), 'destination must not exist; no overwrite')
    require(target.parent.is_dir(), 'destination parent must exist')
    require(target != ROOT and ROOT not in target.parents, 'packet must be outside benchmark repository')
    require(target != skills and skills not in target.parents and target not in skills.parents,
            'packet and skill source must not be nested')
    # Fixed text-only allowlist: no auto-discovery, installation or script execution.
    texts = {stage: read_regular(skills/'skills'/stage/'SKILL.md') for stage in STAGES}
    for data in texts.values():
        require(bool(data.strip()) and b'\x00' not in data, 'skill must be nonempty UTF-8 text')
        data.decode('utf-8')
    require({s: sha256(b) for s, b in texts.items()} == SKILL_HASHES,
            'skill bytes differ from the pinned six-stage revision')
    bindings = source_bindings()
    target.mkdir(mode=0o700)
    try:
        (target/'inputs').mkdir()
        inputs = {}
        for task in ('B02', 'S01'):
            engineering.prepare(task, target/'inputs'/task)
            inputs[task] = snapshot(target/'inputs'/task)[0]
        rows = [('smoke-B02-no-skill', 'B02', 'no-skill', 0, 'smoke')]
        for task in ('B02', 'S01'):
            for repeat in (1, 2, 3):
                arms = ('no-skill', 'workflow') if repeat % 2 else ('workflow', 'no-skill')
                rows.extend((f'{task}-r{repeat}-{arm}', task, arm, repeat, 'comparison') for arm in arms)
        slots = []
        (target/'slots').mkdir()
        for ident, task, arm, repeat, phase in rows:
            slot = target/'slots'/ident
            slot.mkdir()
            shutil.copytree(target/'inputs'/task, slot/'candidate')
            prompt = COMMON_PROMPT
            if arm == 'workflow':
                prompt += ('Follow the six supplied workflow stages in order: ' + ' → '.join(STAGES) + '.\n'
                           'Read workflow/<stage>.md. Deliver-change is local-only; no publishing or pushes.\n'
                           'Do not invoke learn-from-task or retain memory across trials.\n')
                (slot/'workflow').mkdir()
                for stage, data in texts.items():
                    (slot/'workflow'/f'{stage}.md').write_bytes(data)
            (slot/'PROMPT.md').write_text(prompt, encoding='utf-8')
            slots.append({'slot_id': ident, 'task': task, 'arm': arm, 'repeat': repeat, 'phase': phase,
                          'state': 'not_run', 'business_status': 'not_evaluated', 'cost_usd': None,
                          'elapsed_seconds': None, 'prompt_sha256': sha256(prompt.encode()),
                          'input_sha256': inputs[task]['source_sha256']})
        manifest = {'schema_version': 'pilot-preparation-1.0', 'data_class': LABEL,
                    'execution_status': 'not_run', 'launch_supported': False,
                    'workflow': {'repository': 'https://github.com/Wfyywj/agent-skills',
                                 'revision': SKILL_REVISION,
                                 'revision_verification': 'six file SHA256 values pinned from verified public checkout',
                                 'stages': list(STAGES), 'sha256': {s: sha256(b) for s, b in texts.items()},
                                 'adaptation': 'local-delivery-only; learn-from-task excluded',
                                 'semantics': 'skill-context ablation; orchestration requires actual six-stage evidence'},
                    'common_prompt_sha256': sha256(COMMON_PROMPT.encode()),
                    'source_bindings': bindings, 'inputs': inputs, 'slots': slots,
                    'model': None, 'cli_version': None, 'auth_mode': None, 'smoke_cap_usd': None,
                    'blockers': BLOCKERS,
                    'policy': {'track': 'system_workflow_comparison', 'retries': 'none; retain all planned slots',
                               'order': 'B02 then S01; repeats 1/3 control first, repeat 2 workflow first',
                               'smoke': 'one B02 no-skill; excluded from the 12 comparison trials',
                               'isolation': 'directories are NOT security boundaries; never launch from this packet',
                               'results': 'no fabricated results; failures/cancel/missing and unknown costs retained',
                               'privacy': 'raw real traces remain local; review/redact secrets before any publication',
                               'analysis': 'NOT an analysis_tools plan or a real-result importer'}}
        write_json(target/'manifest.json', manifest)
        (target/'README.md').write_text('# Offline pilot packet — NOT RUN\n\n'
            'One smoke + twelve reserved comparison slots; no models or evaluator executed.\n'
            'Every candidate for a task is byte-identical at preparation. Only workflow arms contain six skill texts.\n'
            'Do not launch agents in this directory: sibling trials and source inputs are visible.\n'
            'A future executor must materialize one slot into a fresh disposable environment, mount only that slot,\n'
            'freeze model/config/budget and keep verifier, references, other trials and operator credentials separate.\n'
            'manifest.json lists unresolved launch gates. This is not a runnable recipe or result dataset.\n', encoding='utf-8')
        seal = snapshot(target)[0]
        write_json(target/'seal.json', seal)
    except BaseException:
        shutil.rmtree(target)
        raise
    return {'packet': str(target), 'data_class': LABEL, 'execution_status': 'not_run',
            'smoke_slots': 1, 'comparison_slots': 12, 'launch_supported': False, 'blockers': BLOCKERS}


def verify(destination):
    target = location(destination)
    seal = strict_json(read_regular(target/'seal.json'))
    current = snapshot(target)[0]
    files = [f for f in current['files'] if f['path'] != 'seal.json']
    require(seal == {'files': files, 'source_sha256': sha256(canonical(files)),
                     'total_bytes': sum(f['bytes'] for f in files)}, 'packet changed or seal invalid')
    manifest = strict_json(read_regular(target/'manifest.json'))
    require(manifest['source_bindings'] == source_bindings(), 'benchmark/preparer changed; prepare a new packet')
    return {'integrity': 'unchanged', 'execution_status': 'not_run', 'launch_supported': False,
            'warning': 'Local unsigned seal verifies consistency, not authenticity, readiness or execution'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    make = sub.add_parser('prepare')
    make.add_argument('--skill-root', required=True)
    make.add_argument('--destination', required=True)
    check = sub.add_parser('verify')
    check.add_argument('--destination', required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare(args.skill_root, args.destination) if args.command == 'prepare' else verify(args.destination)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
