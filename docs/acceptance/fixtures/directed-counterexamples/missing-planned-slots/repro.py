#!/usr/bin/env python3
"""Directed counterexample: a missing planned slot must stay incomplete.

The full plan has two preregistered pairs and only three records (repeat 2 arm
B is absent). Analysis must exit 2 with status incomplete and a null paired
delta. plan-cherry-picked.json deletes that pair; it can exit 0, and that is
the view this defense must not produce from the full plan.

Also replays the documented synthetic recipe (6 planned slots, 4 records).
Exit 0 when both paths block the dropped-slot success view.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = next(p for p in [HERE, *HERE.parents] if (p / 'analysis_tools' / 'paired_analysis.py').is_file())
ANALYZER = ROOT / 'analysis_tools' / 'paired_analysis.py'


def run_analyzer(plan, records):
    with tempfile.TemporaryDirectory(prefix='missing-slots-') as temp:
        output = Path(temp) / 'report.json'
        proc = subprocess.run(
            [sys.executable, str(ANALYZER), '--plan', str(plan), '--records', str(records),
             '--allow-synthetic', '--output', str(output)],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        report = json.loads(output.read_text(encoding='utf-8')) if output.is_file() else None
        return proc.returncode, proc.stderr.strip(), report


def recipe_analyze():
    parent = Path(tempfile.mkdtemp(prefix='missing-slots-recipe-'))
    try:
        recipe = parent / 'recipe.json'
        example = subprocess.run(
            [sys.executable, '-m', 'experiment_tools.recipe', 'example'],
            cwd=ROOT, capture_output=True, text=True, timeout=60, check=True,
        )
        recipe.write_text(example.stdout, encoding='utf-8')
        run = parent / 'run'
        for command in (
            ['freeze', '--recipe', str(recipe), '--run', str(run), '--allow-synthetic'],
            ['replay', '--run', str(run), '--allow-synthetic'],
        ):
            step = subprocess.run(
                [sys.executable, '-m', 'experiment_tools.recipe', *command],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            if step.returncode != 0:
                return step.returncode, step.stderr.strip(), None
        analyze = subprocess.run(
            [sys.executable, '-m', 'experiment_tools.recipe', 'analyze', '--run', str(run), '--allow-synthetic'],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        summary = json.loads(analyze.stdout)
        report = json.loads((run / 'analysis' / 'report.json').read_text(encoding='utf-8'))
        return analyze.returncode, summary, report
    finally:
        shutil.rmtree(parent, ignore_errors=True)


def main():
    full_exit, full_err, full = run_analyzer(HERE / 'plan.json', HERE / 'records.json')
    cherry_exit, cherry_err, cherry = run_analyzer(HERE / 'plan-cherry-picked.json', HERE / 'records-cherry-picked.json')
    recipe_exit, recipe_summary, recipe_report = recipe_analyze()
    missing = full['missing_slots'] if full else []
    full_blocks = (
        full_exit == 2 and full is not None
        and full.get('status') == 'incomplete'
        and full['overall']['success_delta_B_minus_A'] is None
        and full['overall']['planned_pairs'] == 2
        and len(missing) == 1
        and missing[0]['repeat'] == 2 and missing[0]['arm'] == 'B'
        and full['overall']['arms']['A']['failures'] == 1
        and full['overall']['arms']['A']['observed'] == 2
        and full['overall']['arms']['B']['success_rate'] is None
    )
    cherry_is_contrast = (
        cherry_exit == 0 and cherry is not None
        and cherry.get('status') == 'complete'
        and cherry['overall']['planned_pairs'] == 1
        and cherry['missing_slots'] == []
    )
    recipe_blocks = (
        recipe_exit == 2 and isinstance(recipe_summary, dict)
        and recipe_summary.get('status') == 'incomplete'
        and recipe_summary.get('records') == 4
        and recipe_summary.get('planned_slots') == 6
        and recipe_report is not None
        and recipe_report.get('status') == 'incomplete'
        and len(recipe_report.get('missing_slots') or []) == 2
        and recipe_report['overall']['success_delta_B_minus_A'] is None
    )
    blocked = full_blocks and cherry_is_contrast and recipe_blocks
    print('class: missing-planned-slots')
    print('audit: TRUSTWORTHY_EXPERIMENTS strict analysis; stage-delivery recipe exit 2')
    print('full_plan_exit: ' + str(full_exit))
    if full:
        print('full_plan: status={status} planned_pairs={pairs} missing={missing} delta={delta} arm_A_failures={failures}'.format(
            status=full.get('status'),
            pairs=full['overall']['planned_pairs'],
            missing=len(missing),
            delta=full['overall']['success_delta_B_minus_A'],
            failures=full['overall']['arms']['A']['failures'],
        ))
    if full_err:
        print('full_plan_stderr: ' + full_err)
    print('cherry_picked_exit: ' + str(cherry_exit))
    if cherry:
        print('cherry_picked: status={status} planned_pairs={pairs} missing={missing}'.format(
            status=cherry.get('status'),
            pairs=cherry['overall']['planned_pairs'],
            missing=len(cherry['missing_slots']),
        ))
    if cherry_err:
        print('cherry_picked_stderr: ' + cherry_err)
    print('recipe_analyze_exit: ' + str(recipe_exit))
    if isinstance(recipe_summary, dict):
        print('recipe_analyze: ' + json.dumps({
            'status': recipe_summary.get('status'),
            'records': recipe_summary.get('records'),
            'planned_slots': recipe_summary.get('planned_slots'),
        }, ensure_ascii=False))
    elif recipe_summary:
        print('recipe_analyze_error: ' + str(recipe_summary))
    print('verdict: ' + ('blocks' if blocked else 'still-fails'))
    return 0 if blocked else 1


if __name__ == '__main__':
    sys.exit(main())
