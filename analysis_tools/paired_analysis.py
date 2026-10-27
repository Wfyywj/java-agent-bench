#!/usr/bin/env python3
"""Offline paired analysis of preregistered, normalized agent trials (stdlib only)."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import random
import re
import sys


class ValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def keys(value, fields, label):
    require(isinstance(value, dict), f'{label}: expected object')
    require(set(value) == set(fields.split()), f'{label}: expected exactly {fields}')


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def timestamp(value):
    require(nonempty(value), 'timestamp must be a timezone-aware ISO timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(parsed.tzinfo is not None, 'timestamp requires timezone')
        return parsed
    except ValueError as exc:
        raise ValidationError(f'invalid timestamp: {value}') from exc


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def identity(value):
    require(nonempty(value['implementation_id']), 'implementation_id required')
    require(isinstance(value['manifest_sha256'], str) and re.fullmatch('[0-9a-f]{64}', value['manifest_sha256']), 'invalid manifest_sha256')
    require(type(value['repeat']) is int and value['repeat'] >= 1, 'repeat must be positive integer')
    return value['implementation_id'], value['manifest_sha256'], value['repeat']


METADATA = 'model tool workflow budget environment evaluator'
TRACKS = {'model': {'model'}, 'workflow': {'tool', 'workflow'}, 'budget': {'budget'},
          'system': {'model', 'tool', 'workflow', 'budget'}}


def metadata(value):
    keys(value, METADATA, 'metadata')
    for field in ('model', 'tool', 'workflow', 'environment', 'evaluator'):
        require(nonempty(value[field]), f'metadata.{field} must be a versioned identifier')
    keys(value['budget'], 'wall_seconds max_tokens max_tool_calls', 'budget')
    for field, amount in value['budget'].items():
        require(number(amount) and amount > 0, f'budget.{field} must be positive')
    for field in ('max_tokens', 'max_tool_calls'):
        require(type(value['budget'][field]) is int, f'budget.{field} must be integer')


def validate(plan, records, allow_synthetic=False):
    keys(plan, 'schema_version plan_id preregistered_at data_class track arms pairs', 'plan')
    require(plan['schema_version'] == '1.0', 'unsupported plan version')
    require(nonempty(plan['plan_id']), 'plan_id required')
    registered = timestamp(plan['preregistered_at'])
    require(plan['data_class'] in ('actual_agent_trials', 'SYNTHETIC TEST FIXTURES NOT MODEL RESULTS'), 'invalid data_class')
    require(allow_synthetic or plan['data_class'] == 'actual_agent_trials', 'synthetic fixtures require --allow-synthetic')
    require(plan['track'] in TRACKS, 'invalid comparison track')
    keys(plan['arms'], 'A B', 'arms')
    for arm in plan['arms'].values():
        metadata(arm)
    differing = {key for key in METADATA.split() if plan['arms']['A'][key] != plan['arms']['B'][key]}
    require(bool(differing), 'arms must differ in a preregistered factor')
    require(differing <= TRACKS[plan['track']], f'incompatible arms for {plan["track"]} track: {sorted(differing)}')
    require(isinstance(plan['pairs'], list) and plan['pairs'], 'nonempty planned pairs required')
    planned = set()
    versions = {}
    for pair in plan['pairs']:
        keys(pair, 'implementation_id manifest_sha256 repeat', 'pair')
        key = identity(pair)
        require(key not in planned, f'duplicate planned pair: {key}')
        require(key[0] not in versions or versions[key[0]] == key[1], f'conflicting manifest versions: {key[0]}')
        versions[key[0]] = key[1]
        planned.add(key)
    require(isinstance(records, list), 'records must be a JSON array')
    indexed = {}
    trial_ids = set()
    for record in records:
        keys(record, 'schema_version plan_id data_class run_kind trial_id implementation_id manifest_sha256 repeat arm started_at metadata outcome elapsed_seconds elapsed_unknown_reason cost_usd cost_unknown_reason evidence', 'record')
        require(record['schema_version'] == '1.0' and record['plan_id'] == plan['plan_id'], 'record plan/version mismatch')
        require(record['data_class'] == plan['data_class'], 'mixed synthetic/actual records')
        require(record['run_kind'] == 'agent_trial', 'selfcheck/localreference are not agent trials')
        require(nonempty(record['trial_id']) and record['trial_id'] not in trial_ids, 'missing/duplicate trial_id')
        trial_ids.add(record['trial_id'])
        key = identity(record)
        require(key in planned, f'unplanned task/version/repeat: {key}')
        require(record['arm'] in ('A', 'B'), 'invalid arm')
        key += (record['arm'],)
        require(key not in indexed, f'duplicate slot: {key}')
        metadata(record['metadata'])
        require(record['metadata'] == plan['arms'][record['arm']], 'record metadata mismatch with locked arm')
        require(timestamp(record['started_at']) >= registered, 'trial predates preregistration')
        require(record['outcome'] in ('success', 'failure', 'infrastructure_failure'), 'invalid outcome')
        for field, reason in [('elapsed_seconds', 'elapsed_unknown_reason'), ('cost_usd', 'cost_unknown_reason')]:
            require((record[field] is None and nonempty(record[reason])) or
                    (number(record[field]) and record[reason] is None), f'{field}: nonnegative finite number with null reason, or null with reason required')
        keys(record['evidence'], 'agent_trace_sha256 evaluation_sha256', 'evidence')
        for digest in record['evidence'].values():
            require(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), 'agent trace and evaluation evidence SHA256 required')
        indexed[key] = record
    return sorted(planned), indexed, sorted(differing)


def summarize(pairs, indexed):
    n = len(pairs)
    arms = {}
    for arm in ('A', 'B'):
        rows = [indexed[pair + (arm,)] for pair in pairs if pair + (arm,) in indexed]
        counts = Counter(row['outcome'] for row in rows)
        summary = {'planned': n, 'observed': len(rows), 'missing': n-len(rows),
                   'successes': counts['success'], 'failures': counts['failure'],
                   'infrastructure_failures': counts['infrastructure_failure'],
                   'success_rate': counts['success']/n if len(rows) == n else None,
                   'success_rate_bounds': [counts['success']/n, (counts['success']+n-len(rows))/n]}
        for field in ('elapsed_seconds', 'cost_usd'):
            known = [row[field] for row in rows if row[field] is not None]
            summary[field] = {'known_count': len(known), 'unknown_count': len(rows)-len(known),
                              'missing_count': n-len(rows), 'known_sum': sum(known),
                              'total': sum(known) if len(known) == n else None,
                              'unknown_reasons': dict(Counter(row['elapsed_unknown_reason' if field == 'elapsed_seconds' else 'cost_unknown_reason'] for row in rows if row[field] is None))}
        arms[arm] = summary
    complete_pairs = [pair for pair in pairs if all(pair+(arm,) in indexed for arm in ('A', 'B'))]
    wins = Counter()
    for pair in complete_pairs:
        a, b = (indexed[pair+(arm,)]['outcome'] == 'success' for arm in ('A', 'B'))
        wins['B_only' if b and not a else 'A_only' if a and not b else 'both_success' if a else 'neither_success'] += 1
    complete = len(complete_pairs) == n
    resources = {}
    for field in ('elapsed_seconds', 'cost_usd'):
        differences = [indexed[pair+('B',)][field] - indexed[pair+('A',)][field]
                       for pair in complete_pairs
                       if all(indexed[pair+(arm,)][field] is not None for arm in ('A', 'B'))]
        resources[field] = {
            'both_known_pairs': len(differences),
            'unknown_value_pairs': len(complete_pairs)-len(differences),
            'missing_record_pairs': n-len(complete_pairs),
            'mean_delta_B_minus_A': sum(differences)/n if len(differences) == n else None,
            'both_known_subset_mean_delta_B_minus_A': sum(differences)/len(differences) if differences else None,
        }
    return {'planned_pairs': n, 'complete_pairs': len(complete_pairs), 'arms': arms,
            'paired_resources': resources,
            'paired_outcomes': {key: wins[key] for key in ('A_only', 'B_only', 'both_success', 'neither_success')},
            'success_delta_B_minus_A': (wins['B_only']-wins['A_only'])/n if complete else None}


def analyze(plan, records, allow_synthetic=False, bootstrap_samples=0, seed=1729):
    require(type(bootstrap_samples) is int and 0 <= bootstrap_samples <= 100000, 'bootstrap samples must be 0..100000')
    require(type(seed) is int, 'seed must be integer')
    pairs, indexed, differing = validate(plan, records, allow_synthetic)
    missing = [dict(implementation_id=p[0], manifest_sha256=p[1], repeat=p[2], arm=a)
               for p in pairs for a in ('A', 'B') if p+(a,) not in indexed]
    groups = {task: [p for p in pairs if p[0] == task] for task in sorted({p[0] for p in pairs})}
    report = {'schema_version': '1.0', 'plan_id': plan['plan_id'], 'data_class': plan['data_class'],
              'plan_sha256': hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
              'status': 'incomplete' if missing else 'complete', 'track': plan['track'],
              'arm_metadata': plan['arms'], 'differing_factors': differing,
              'denominator_policy': 'All preregistered pairs; infrastructure failures count as non-success. Missing trials are not imputed: primary delta withheld, arm bounds shown. No failed trial is dropped.',
              'missing_slots': missing, 'overall': summarize(pairs, indexed),
              'per_task': {task: summarize(group, indexed) for task, group in groups.items()},
              'warnings': ['Metadata and evidence hashes are declarations, not independent verification of provenance or preregistration.'],
              'bootstrap': None}
    if len(groups) < 20:
        report['warnings'].append('Small task sample (<20 clusters): estimates and intervals can be unstable; no significance claim is supported.')
    if bootstrap_samples:
        if missing:
            report['warnings'].append('Bootstrap withheld because planned trials are missing.')
        else:
            require(bootstrap_samples >= 100, 'bootstrap requires at least 100 samples')
            rng = random.Random(seed)
            clusters = list(groups.values())
            estimates = []
            for _ in range(bootstrap_samples):
                sampled = [p for _ in clusters for p in rng.choice(clusters)]
                estimates.append(sum(int(indexed[p+('B',)]['outcome'] == 'success') - int(indexed[p+('A',)]['outcome'] == 'success') for p in sampled) / len(sampled))
            estimates.sort()
            report['bootstrap'] = {'method': 'task-cluster percentile bootstrap; all repeats travel with task; pair-weighted delta',
                                   'samples': bootstrap_samples, 'seed': seed, 'task_clusters': len(clusters),
                                   'interval_level': 0.95, 'interval': [estimates[math.floor(.025*(len(estimates)-1))], estimates[math.ceil(.975*(len(estimates)-1))]]}
    return report


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValidationError(f'nonfinite JSON: {value}')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--records', required=True)
    parser.add_argument('--output', help='JSON output path (default stdout)')
    parser.add_argument('--allow-synthetic', action='store_true')
    parser.add_argument('--bootstrap-samples', type=int, default=0)
    parser.add_argument('--seed', type=int, default=1729)
    args = parser.parse_args()
    try:
        report = analyze(load_json(args.plan), load_json(args.records), args.allow_synthetic, args.bootstrap_samples, args.seed)
        rendered = json.dumps(report, indent=2, allow_nan=False) + '\n'
        if args.output:
            Path(args.output).write_text(rendered, encoding='utf-8')
        else:
            print(rendered, end='')
        return 0 if report['status'] == 'complete' else 2
    except (ValidationError, OSError, ValueError, TypeError) as exc:
        print(f'Invalid analysis input: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
