"""Public independent decimal oracle and structured review checks; no LLM grader."""
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def oracle(case):
    amounts = [Decimal(x) for x in case['prices']]
    discount = Decimal('0' if case['discount'] == '-' else case['discount'])
    tax = Decimal(case['tax'])
    limit = Decimal('999999999.99')
    if not 0 <= discount <= 1 or not 0 <= tax <= 1 or any(x < 0 or x > limit for x in amounts):
        return 'ERROR\t422\tINVALID_QUOTE'
    cents = Decimal('.01')
    subtotal = sum((x * (1-discount)).quantize(cents, rounding=ROUND_HALF_UP) for x in amounts)
    total = subtotal + (subtotal * tax).quantize(cents, rounding=ROUND_HALF_UP)
    return 'ERROR\t422\tINVALID_QUOTE' if total > limit else f'OK\t{total:.2f}'

def cases():
    fixed = json.loads((ROOT/'verifier/cases.json').read_text())
    for case in fixed:
        assert oracle(case) == case['expected'], case['id']
    # Independent deterministic decimal grid, not reference output harvesting.
    for i in range(1, 32):
        case = dict(id=f'grid-{i}', prices=[f'{i}.005','0.015','1.035'], discount=['0','.1','.25'][i%3], tax=['0','.05','.2'][i%3])
        case['expected'] = oracle(case)
        fixed.append(case)
    return fixed

def verify_review(path):
    actual = json.loads(Path(path).read_text())
    frozen = json.loads((ROOT/'verifier/verdict-fixture.json').read_text())
    failures = []
    if not isinstance(actual,dict) or not isinstance(actual.get('findings'),list) or not isinstance(actual.get('checked_safe'),list) or not isinstance(actual.get('nonblocking'),list):
        return ['invalid review structure']
    if any(not isinstance(x,dict) or not isinstance(x.get('id'),str) for x in actual['findings']): return ['invalid finding structure']
    if any(not isinstance(x,str) for x in actual['checked_safe']): return ['invalid checked_safe structure']
    if any(not isinstance(x,dict) or x.get('severity')!='suggestion' for x in actual['nonblocking']): return ['blocking/invalid item in nonblocking suggestions']
    actual_findings = {x['id']:x for x in actual['findings']}
    wanted = {x['id']:x for x in frozen['findings']}
    if len(actual_findings) != len(actual['findings']): failures.append('duplicate finding')
    if set(actual_findings) != set(wanted): failures.append('missing or unsupported blocker')
    for ident in set(actual_findings)&set(wanted):
        if actual_findings[ident] != wanted[ident]: failures.append('incorrect anchor: '+ident)
    if set(actual['checked_safe']) != set(frozen['checked_safe']): failures.append('unchecked safe boundaries')
    if not any(x.get('kind')=='readability' and x.get('severity')=='suggestion' for x in actual['nonblocking']):
        failures.append('suggestion classification')
    return failures
