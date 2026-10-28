"""Bounded synthetic-only recipe replay. No subprocess, model or candidate execution."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from analysis_tools.paired_analysis import analyze, keys, require, timestamp, validate
from cli_adapters.common import canonical, read_regular, sha256, strict_json
from cli_adapters.collection import snapshot
from experiment_tools.workspace import ROOT, initialize, location, task_identity, write_json

LABEL = 'SYNTHETIC TEST FIXTURES NOT MODEL RESULTS'
STATES = ('success', 'failure', 'infrastructure_failure', 'missing', 'cancelled')
POLICY = {'assignment': 'pair order, A then B; no retries',
          'outcomes': 'explicit synthetic fixture assertions; never evaluator or CLI inference',
          'cancelled': 'no attempted trial; retain ledger entry and missing analysis slot',
          'resources': 'unknown; replay runtime is not agent wall time or model cost',
          'execution': 'synthetic-only; no actual execution/import supported'}


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return strict_json(read_regular(location(path)))


def digest(value):
    return sha256(canonical(value))


def permitted(allow_synthetic):
    require(allow_synthetic, 'explicit --allow-synthetic required; actual execution/import unsupported')


def example():
    """Explicit fixture configuration, not invented actual model metadata."""
    arms = {}
    for arm in ('A', 'B'):
        arms[arm] = {'model': 'synthetic-model-' + arm + '@fixture-v1',
                     'tool': 'synthetic-cli@fixture-v1', 'workflow': 'synthetic-prompt@fixture-v1',
                     'budget': {'wall_seconds': 120, 'max_tokens': 1000, 'max_tool_calls': 20},
                     'environment': 'synthetic-environment@fixture-v1',
                     'evaluator': 'synthetic-assertions@fixture-v1-not-executed'}
    return {'schema_version': 'recipe-1.0', 'data_class': LABEL, 'recipe_id': 'B01-offline-replay',
            'task': 'B01', 'track': 'model', 'arms': arms,
            'repeats': [{'repeat': 1, 'A': 'failure', 'B': 'success'},
                        {'repeat': 2, 'A': 'infrastructure_failure', 'B': 'cancelled'},
                        {'repeat': 3, 'A': 'missing', 'B': 'failure'}], 'policy': POLICY}


def validate_recipe(recipe):
    keys(recipe, 'schema_version data_class recipe_id task track arms repeats policy', 'recipe')
    require(recipe['schema_version'] == 'recipe-1.0' and recipe['data_class'] == LABEL,
            'only explicitly synthetic recipe-1.0 is supported')
    require(recipe['task'] == 'B01', 'bounded bridge supports B01 only')
    require(recipe['policy'] == POLICY, 'unsupported replay policy')
    require(isinstance(recipe['repeats'], list) and 1 <= len(recipe['repeats']) <= 100,
            'recipe requires 1..100 repeats')
    seen = set()
    for entry in recipe['repeats']:
        keys(entry, 'repeat A B', 'repeat')
        require(type(entry['repeat']) is int and entry['repeat'] > 0 and entry['repeat'] not in seen,
                'repeat must be positive and unique')
        seen.add(entry['repeat'])
        require(all(entry[a] in STATES for a in ('A', 'B')), 'unsupported synthetic state')
    # Delegate exact metadata, track and identity constraints to the unchanged strict analyzer.
    validate(make_plan(recipe, '2000-01-01T00:00:00Z'), [], allow_synthetic=True)


def make_plan(recipe, frozen_at):
    _, implementation, source = task_identity(recipe['task'])
    return {'schema_version': '1.0', 'plan_id': recipe['recipe_id'], 'preregistered_at': frozen_at,
            'data_class': LABEL, 'track': recipe['track'], 'arms': recipe['arms'],
            'pairs': [{'implementation_id': implementation, 'manifest_sha256': sha256(read_regular(source/'task.json')),
                       'repeat': e['repeat']} for e in recipe['repeats']]}


def bindings():
    """Bind task inputs plus actual bridge/preparer/analysis implementation bytes."""
    _, _, source = task_identity('B01')
    files = {}
    for relative, data in snapshot(source)[1].items():
        if '__pycache__' not in Path(relative).parts and not relative.endswith('.pyc'):
            files[str(source.relative_to(ROOT)/relative)] = sha256(data)
    for directory in ('experiment_tools', 'cli_adapters', 'analysis_tools'):
        for file in sorted((ROOT/directory).glob('*.py')):
            files[str(file.relative_to(ROOT))] = sha256(read_regular(file))
    for file in ('experiment_tools/recipe.schema.json', 'analysis_tools/input.schema.json'):
        files[file] = sha256(read_regular(ROOT/file))
    files['scripts/engineering.py'] = sha256(read_regular(ROOT/'scripts/engineering.py'))
    return files


def fresh_target(value):
    target = location(value)
    require(not target.exists(), 'target must not exist; no overwrite or refreeze')
    require(target.parent.is_dir(), 'target parent must exist')
    require(target != ROOT and ROOT not in target.parents, 'run must be outside benchmark repository')
    return target


def freeze(recipe_path, run, allow_synthetic=False):
    permitted(allow_synthetic)
    recipe = load(recipe_path)
    validate_recipe(recipe)
    target = fresh_target(run)
    frozen = {'schema_version': 'frozen-recipe-1.0', 'recipe': recipe,
              'plan': make_plan(recipe, now()), 'bindings': bindings(), 'run_directory': str(target)}
    frozen['freeze_sha256'] = digest(frozen)
    target.mkdir(mode=0o700)
    try:
        write_json(target/'frozen.json', frozen)
        write_json(target/'plan.json', frozen['plan'])
        (target/'slots').mkdir()
        for pair in frozen['plan']['pairs']:
            for arm in ('A', 'B'):
                slot = target/'slots'/slot_id(pair, arm)
                initialize('B01', 'codex', recipe['arms'][arm]['model'], 'synthetic-cli-version', str(slot))
        # Includes independent baseline/candidate identity, before replay can change anything.
        seal = {'freeze_sha256': frozen['freeze_sha256'], 'workspaces': {}}
        for slot in sorted((target/'slots').iterdir()):
            seal['workspaces'][slot.name] = snapshot(slot)[0]['source_sha256']
        write_json(target/'workspace-seal.json', seal)
    except BaseException:
        shutil.rmtree(target)
        raise
    return {'run': str(target), 'data_class': LABEL, 'freeze_sha256': frozen['freeze_sha256'],
            'planned_slots': len(frozen['plan']['pairs'])*2, 'execution': 'not_attempted'}


def slot_id(pair, arm):
    return 'repeat-' + str(pair['repeat']) + '-' + arm


def verified(run):
    target = location(run)
    frozen = load(target/'frozen.json')
    keys(frozen, 'schema_version recipe plan bindings run_directory freeze_sha256', 'frozen')
    require(frozen['schema_version'] == 'frozen-recipe-1.0', 'unsupported freeze version')
    require(frozen['run_directory'] == str(target), 'run moved; create a new run')
    require(frozen['freeze_sha256'] == digest({k: v for k, v in frozen.items() if k != 'freeze_sha256'}),
            'frozen content hash mismatch')
    validate_recipe(frozen['recipe'])
    require(frozen['plan'] == make_plan(frozen['recipe'], frozen['plan']['preregistered_at']), 'plan/task version mismatch')
    require(load(target/'plan.json') == frozen['plan'], 'plan altered')
    require(frozen['bindings'] == bindings(), 'source/evaluator/bridge version mismatch; create a new run')
    return target, frozen


def source_hash(slot):
    manifest = snapshot(slot/'candidate')[0]
    # PREPARED.json records preparation time; it is a run artifact, not submission content.
    return digest([f for f in manifest['files'] if f['path'] != 'PREPARED.json'])


def replay(run, allow_synthetic=False):
    permitted(allow_synthetic)
    target, frozen = verified(run)
    output = target/'replay'
    require(not output.exists(), 'replay is immutable; create a new frozen run instead of retry/overwrite')
    seal = load(target/'workspace-seal.json')
    require(seal == {'freeze_sha256': frozen['freeze_sha256'], 'workspaces': {
        slot_id(p, a): snapshot(target/'slots'/slot_id(p, a))[0]['source_sha256']
        for p in frozen['plan']['pairs'] for a in ('A', 'B')}}, 'workspace changed before replay')
    output.mkdir()
    envelopes = []
    # Do not erase a partial replay on error; an incomplete attempt must remain visible.
    for pair, state in zip(frozen['plan']['pairs'], frozen['recipe']['repeats']):
        for arm in ('A', 'B'):
            ident = slot_id(pair, arm)
            slot = target/'slots'/ident
            envelope = {'schema_version': 'trial-envelope-1.0', 'data_class': LABEL,
                        'run_kind': 'synthetic_replay', 'freeze_sha256': frozen['freeze_sha256'],
                        'slot_id': ident, 'identity': dict(pair, arm=arm), 'metadata': frozen['plan']['arms'][arm],
                        'state': state[arm], 'replayed_at': now(),
                        'source_content_sha256': source_hash(slot),
                        'workspace_artifact_sha256': snapshot(slot)[0]['source_sha256'],
                        'elapsed_seconds': None, 'cost_usd': None,
                        'resource_unknown_reason': 'No actual agent execution or resource measurement',
                        'evidence': None}
            if state[arm] not in ('missing', 'cancelled'):
                evidence = {}
                for kind in ('trace', 'evaluation'):
                    value = {'data_class': LABEL, 'run_kind': 'synthetic_replay', 'slot_id': ident,
                             'freeze_sha256': frozen['freeze_sha256'], 'kind': kind,
                             'fixture_assertion': state[arm], 'execution': 'not_attempted'}
                    name = ident + '-' + kind + '.json'
                    write_json(output/name, value)
                    evidence[kind] = {'path': name, 'sha256': sha256(read_regular(output/name))}
                envelope['evidence'] = evidence
            envelope['run_artifact_sha256'] = digest(envelope)
            write_json(output/(ident + '.json'), envelope)
            envelopes.append(envelope)
    write_json(output/'ledger.json', {'data_class': LABEL, 'freeze_sha256': frozen['freeze_sha256'], 'slots': envelopes})
    return {'run': str(target), 'data_class': LABEL, 'planned_slots': len(envelopes), 'execution': 'not_attempted'}


def export_analysis(run, allow_synthetic=False):
    permitted(allow_synthetic)
    target, frozen = verified(run)
    output = target/'analysis'
    require(not output.exists(), 'analysis output exists; no overwrite')
    ledger = load(target/'replay'/'ledger.json')
    keys(ledger, 'data_class freeze_sha256 slots', 'ledger')
    require(ledger['data_class'] == LABEL and ledger['freeze_sha256'] == frozen['freeze_sha256'], 'ledger identity mismatch')
    expected = [(p, a, state[a]) for p, state in zip(frozen['plan']['pairs'], frozen['recipe']['repeats']) for a in ('A', 'B')]
    require(isinstance(ledger['slots'], list) and len(ledger['slots']) == len(expected), 'ledger must retain every planned slot')
    records = []
    for envelope, (pair, arm, state) in zip(ledger['slots'], expected):
        keys(envelope, 'schema_version data_class run_kind freeze_sha256 slot_id identity metadata state replayed_at source_content_sha256 workspace_artifact_sha256 elapsed_seconds cost_usd resource_unknown_reason evidence run_artifact_sha256', 'envelope')
        ident = slot_id(pair, arm)
        require(envelope == load(target/'replay'/(ident+'.json')), 'envelope/ledger mismatch')
        require(envelope['run_artifact_sha256'] == digest({k:v for k,v in envelope.items() if k != 'run_artifact_sha256'}), 'envelope digest mismatch')
        require(envelope['schema_version'] == 'trial-envelope-1.0' and envelope['data_class'] == LABEL and
                envelope['run_kind'] == 'synthetic_replay' and envelope['freeze_sha256'] == frozen['freeze_sha256'] and
                envelope['slot_id'] == ident and envelope['identity'] == dict(pair, arm=arm) and
                envelope['metadata'] == frozen['plan']['arms'][arm] and envelope['state'] == state, 'envelope identity/state mismatch')
        slot = target/'slots'/ident
        require(envelope['source_content_sha256'] == source_hash(slot) and envelope['workspace_artifact_sha256'] == snapshot(slot)[0]['source_sha256'], 'workspace evidence changed')
        require(timestamp(envelope['replayed_at']) >= timestamp(frozen['plan']['preregistered_at']), 'replay predates freeze')
        require(envelope['elapsed_seconds'] is None and envelope['cost_usd'] is None and envelope['resource_unknown_reason'] == 'No actual agent execution or resource measurement', 'synthetic resources must remain unknown')
        if state in ('missing', 'cancelled'):
            require(envelope['evidence'] is None, 'unattempted slot cannot carry trial evidence')
            continue
        keys(envelope['evidence'], 'trace evaluation', 'evidence')
        for kind in ('trace', 'evaluation'):
            ev = envelope['evidence'][kind]
            keys(ev, 'path sha256', 'artifact')
            require(ev['path'] == ident+'-'+kind+'.json', 'unexpected evidence path')
            raw = read_regular(target/'replay'/ev['path'])
            require(sha256(raw) == ev['sha256'], 'evidence byte hash mismatch')
            require(strict_json(raw) == {'data_class': LABEL, 'run_kind': 'synthetic_replay', 'slot_id': ident,
                    'freeze_sha256': frozen['freeze_sha256'], 'kind': kind, 'fixture_assertion': state,
                    'execution': 'not_attempted'}, 'not matching synthetic evidence; reference/selfcheck/actual imports rejected')
        records.append(dict(pair, schema_version='1.0', plan_id=frozen['plan']['plan_id'], data_class=LABEL,
                            run_kind='synthetic_replay', trial_id=ident, arm=arm, started_at=envelope['replayed_at'],
                            metadata=envelope['metadata'], outcome=state, elapsed_seconds=None,
                            elapsed_unknown_reason=envelope['resource_unknown_reason'], cost_usd=None,
                            cost_unknown_reason=envelope['resource_unknown_reason'], evidence={
                                'agent_trace_sha256': envelope['evidence']['trace']['sha256'],
                                'evaluation_sha256': envelope['evidence']['evaluation']['sha256']}))
    report = analyze(frozen['plan'], records, allow_synthetic=True)
    output.mkdir()
    write_json(output/'records.json', records)
    write_json(output/'report.json', report)
    # Separate UI handoff: do NOT masquerade as the existing website importer schema.
    write_json(output/'display.json', {'schema_version': 'synthetic-replay-display-1.0', 'data_class': LABEL,
        'website_import_supported': False, 'freeze_sha256': frozen['freeze_sha256'],
        'slots': ledger['slots'], 'analysis': report})
    return {'run': str(target), 'data_class': LABEL, 'status': report['status'],
            'records': len(records), 'planned_slots': len(expected), 'website_import_supported': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('example')
    p = sub.add_parser('freeze'); p.add_argument('--recipe', required=True); p.add_argument('--run', required=True); p.add_argument('--allow-synthetic', action='store_true')
    for name in ('replay', 'analyze'):
        p = sub.add_parser(name); p.add_argument('--run', required=True); p.add_argument('--allow-synthetic', action='store_true')
    args = vars(parser.parse_args(argv)); command = args.pop('command')
    try:
        if command == 'example': result = example()
        elif command == 'freeze': result = freeze(args.pop('recipe'), **args)
        elif command == 'replay': result = replay(**args)
        else: result = export_analysis(**args)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 2 if result.get('status') == 'incomplete' else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
