#!/usr/bin/env python3
"""Directed counterexample: synthetic fixtures must not pass as real trials.

Recipe freeze rejects data_class actual_agent_trials. Replay evidence whose
run_kind is selfcheck, localreference, or reference, or whose data_class is
actual, is rejected. The generated display keeps website_import_supported
false. The ordinary website importer does not take that display; the synthetic
page does not take ordinary result schemas.

Exit 0 when those gates block the impersonation. This is not a B2 CLI trial
and not a model score.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = next(p for p in [HERE, *HERE.parents] if (p / 'experiment_tools' / 'recipe.py').is_file())
KINDS = ('selfcheck', 'localreference', 'reference')


def recipe_cli(args, timeout=60):
    return subprocess.run(
        [sys.executable, '-m', 'experiment_tools.recipe', *args],
        cwd=ROOT, capture_output=True, text=True, timeout=timeout,
    )


def error_text(proc):
    text = (proc.stderr or proc.stdout or '').strip()
    try:
        return json.loads(proc.stderr).get('error', text)
    except (json.JSONDecodeError, TypeError):
        return text


def reject_actual_recipe():
    parent = Path(tempfile.mkdtemp(prefix='synthetic-actual-'))
    run = parent / 'run'
    try:
        proc = recipe_cli(['freeze', '--recipe', str(HERE / 'recipe-actual.json'), '--run', str(run), '--allow-synthetic'])
        return proc.returncode, error_text(proc), run.exists()
    finally:
        shutil.rmtree(parent, ignore_errors=True)


def reject_without_opt_in():
    parent = Path(tempfile.mkdtemp(prefix='synthetic-opt-'))
    recipe = parent / 'recipe.json'
    run = parent / 'run'
    try:
        example = recipe_cli(['example'])
        if example.returncode != 0:
            return example.returncode, error_text(example), True
        recipe.write_text(example.stdout, encoding='utf-8')
        proc = recipe_cli(['freeze', '--recipe', str(recipe), '--run', str(run)])
        return proc.returncode, error_text(proc), run.exists()
    finally:
        shutil.rmtree(parent, ignore_errors=True)


def synthetic_run():
    parent = Path(tempfile.mkdtemp(prefix='synthetic-replay-'))
    recipe = parent / 'recipe.json'
    run = parent / 'run'
    example = recipe_cli(['example'])
    if example.returncode != 0:
        shutil.rmtree(parent, ignore_errors=True)
        raise SystemExit(example.stderr)
    recipe.write_text(example.stdout, encoding='utf-8')
    for command in (
        ['freeze', '--recipe', str(recipe), '--run', str(run), '--allow-synthetic'],
        ['replay', '--run', str(run), '--allow-synthetic'],
    ):
        step = recipe_cli(command)
        if step.returncode != 0:
            shutil.rmtree(parent, ignore_errors=True)
            raise SystemExit(error_text(step))
    return parent, run


def tamper_evidence(run):
    """Rewrite fixture evidence and refresh its declared hashes.

    A stale sha256 fails earlier as byte mismatch. Recomputing the evidence
    hash and envelope digest reaches the packaging check: selfcheck,
    localreference, reference, and actual data_class are still rejected.
    """
    sys.path.insert(0, str(ROOT))
    from experiment_tools.recipe import digest, write_json
    from cli_adapters.common import canonical, sha256
    replay = run / 'replay'
    paths = [replay / 'repeat-1-A-trace.json', replay / 'repeat-1-A.json', replay / 'ledger.json']
    originals = {path: path.read_bytes() for path in paths}
    messages = []
    try:
        for kind in (*KINDS, 'actual_data_class'):
            for path, data in originals.items():
                path.write_bytes(data)
            document = json.loads(originals[paths[0]])
            if kind == 'actual_data_class':
                document['data_class'] = 'actual_agent_trials'
            else:
                document['run_kind'] = kind
            raw = canonical(document) + b'\n'
            paths[0].write_bytes(raw)
            envelope = json.loads(originals[paths[1]])
            envelope['evidence']['trace']['sha256'] = sha256(raw)
            body = {key: value for key, value in envelope.items() if key != 'run_artifact_sha256'}
            envelope['run_artifact_sha256'] = digest(body)
            write_json(paths[1], envelope)
            ledger = json.loads(originals[paths[2]])
            ledger['slots'] = [envelope if slot.get('slot_id') == 'repeat-1-A' else slot for slot in ledger['slots']]
            write_json(paths[2], ledger)
            proc = recipe_cli(['analyze', '--run', str(run), '--allow-synthetic'])
            message = error_text(proc)
            messages.append(kind + ': ' + message)
            if proc.returncode != 1 or 'reference/selfcheck/actual imports rejected' not in message or (run / 'analysis').exists():
                return False, messages
        return True, messages
    finally:
        for path, data in originals.items():
            path.write_bytes(data)


def reject_record_packaging(run):
    sys.path.insert(0, str(ROOT))
    from analysis_tools.paired_analysis import ValidationError, validate
    plan = json.loads((run / 'plan.json').read_text(encoding='utf-8'))
    records = json.loads((run / 'analysis' / 'records.json').read_text(encoding='utf-8'))
    kind_rejects = []
    for kind in KINDS:
        modified = json.loads(json.dumps(records))
        modified[0]['run_kind'] = kind
        try:
            validate(plan, modified, True)
        except ValidationError as exc:
            kind_rejects.append('not agent trials' in str(exc))
        else:
            kind_rejects.append(False)
    relabeled = json.loads(json.dumps(records))
    relabeled_plan = json.loads(json.dumps(plan))
    relabeled_plan['data_class'] = 'actual_agent_trials'
    for record in relabeled:
        record['data_class'] = 'actual_agent_trials'
    try:
        validate(relabeled_plan, relabeled, True)
    except ValidationError as exc:
        actual_rejected = 'synthetic_replay' in str(exc) or 'not agent trials' in str(exc)
    else:
        actual_rejected = False
    bare = subprocess.run(
        [sys.executable, str(ROOT / 'analysis_tools' / 'paired_analysis.py'),
         '--plan', str(run / 'plan.json'), '--records', str(run / 'analysis' / 'records.json')],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    return all(kind_rejects), actual_rejected, bare.returncode, (bare.stderr or '').strip()


def main():
    actual_exit, actual_error, actual_run_created = reject_actual_recipe()
    opt_exit, opt_error, opt_run_created = reject_without_opt_in()
    parent, run = synthetic_run()
    try:
        evidence_rejected, evidence_messages = tamper_evidence(run)
        analyze = recipe_cli(['analyze', '--run', str(run), '--allow-synthetic'])
        summary = json.loads(analyze.stdout) if analyze.returncode in (0, 2) else {}
        display = json.loads((run / 'analysis' / 'display.json').read_text(encoding='utf-8')) if (run / 'analysis' / 'display.json').is_file() else {}
        kinds_rejected, actual_records_rejected, bare_exit, bare_error = reject_record_packaging(run)
        website = subprocess.run(
            ['node', str(HERE / 'check_website_import.mjs'), str(run / 'analysis' / 'display.json')],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        try:
            website_report = json.loads(website.stdout)
        except json.JSONDecodeError:
            website_report = {'verdict': 'still-fails', 'stdout': website.stdout, 'stderr': website.stderr}
        slots = display.get('slots') or []
        blocked = (
            actual_exit == 1 and not actual_run_created and 'only explicitly synthetic' in actual_error
            and opt_exit == 1 and not opt_run_created and 'allow-synthetic' in opt_error
            and evidence_rejected
            and analyze.returncode == 2
            and summary.get('website_import_supported') is False
            and display.get('website_import_supported') is False
            and display.get('data_class') == 'SYNTHETIC TEST FIXTURES NOT MODEL RESULTS'
            and display.get('schema_version') == 'synthetic-replay-display-1.0'
            and slots and all(slot.get('run_kind') == 'synthetic_replay' for slot in slots)
            and kinds_rejected and actual_records_rejected and bare_exit == 1
            and website.returncode == 0 and website_report.get('verdict') == 'blocks'
        )
        print('class: synthetic-impersonation')
        print('audit: TRUSTWORTHY_EXPERIMENTS data isolation; website_import_supported false')
        print('actual_recipe_exit: ' + str(actual_exit))
        print('actual_recipe_error: ' + actual_error)
        print('actual_run_created: ' + str(actual_run_created))
        print('allow_synthetic_omitted_exit: ' + str(opt_exit))
        print('allow_synthetic_omitted_error: ' + opt_error)
        print('evidence_rejected: ' + str(evidence_rejected))
        for line in evidence_messages:
            print('evidence_probe: ' + line)
        print('analyze_exit: ' + str(analyze.returncode))
        print('website_import_supported=' + str(display.get('website_import_supported')).lower())
        print('display_schema: ' + str(display.get('schema_version')))
        print('record_run_kinds_rejected: ' + str(kinds_rejected))
        print('relabel_actual_with_synthetic_replay_rejected: ' + str(actual_records_rejected))
        print('synthetic_records_without_opt_in_exit: ' + str(bare_exit))
        print('synthetic_records_without_opt_in_error: ' + bare_error)
        print('website_check_exit: ' + str(website.returncode))
        print('website_check: ' + json.dumps(website_report, ensure_ascii=False))
        if website.stderr.strip():
            print('website_check_stderr: ' + website.stderr.strip())
        print('verdict: ' + ('blocks' if blocked else 'still-fails'))
        return 0 if blocked else 1
    finally:
        shutil.rmtree(parent, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
