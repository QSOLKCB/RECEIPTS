"""Offline verification of the saved Codex experiment. Apache-2.0."""
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'src'))
from receipts.evaluation import request_payload, score, summarize
from receipts.evidence import canonical_hash


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def calculate(rows, gold):
    variants = {}
    for variant in ('baseline', 'receipts'):
        selected = [r for r in rows if r['variant'] == variant]
        usage = [r['response']['usage'] for r in selected if 'response' in r]
        stats = {k: sum(u[k] for u in usage)
                 for k in ('input_tokens', 'output_tokens', 'total_tokens')}
        stats['cached_input_tokens'] = sum(u['input_tokens_details']['cached_tokens'] for u in usage)
        stats['reasoning_tokens'] = sum(u['output_tokens_details']['reasoning_tokens'] for u in usage)
        stats['estimated_usd'] = str((
            Decimal(stats['input_tokens'] - stats['cached_input_tokens']) * Decimal('1.75')
            + Decimal(stats['cached_input_tokens']) * Decimal('0.175')
            + Decimal(stats['output_tokens']) * Decimal('14')) / Decimal(1_000_000))
        stats['record_status_counts'] = dict(Counter(r['status'] for r in selected))
        stats['provider_status_counts'] = dict(Counter(r['response']['status'] for r in selected if 'response' in r))
        stats['mismatches_or_invalid'] = [r['case_id'] for r in selected if not r.get('score', {}).get('verdict_correct')]
        stats['unsupported_contradiction_against_frozen_gold_valid_only'] = sum(
            r.get('score', {}).get('valid', False)
            and r['answer']['verdict'] == 'contradicted'
            and gold[r['case_id']]['verdict'] != 'contradicted' for r in selected)
        stats['verdict_text_correct_including_invalid_ids'] = sum(
            isinstance(r.get('answer'), dict)
            and r['answer'].get('verdict') == gold[r['case_id']]['verdict'] for r in selected)
        variants[variant] = stats
    return variants


def main():
    for line in (ROOT / 'SHA256SUMS.txt').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert Path(name).name == name
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    manifest, cases, gold, prompts = [load(n + '.json') for n in ('manifest', 'cases', 'gold', 'prompts')]
    review = load('review-metrics.json')
    rows = [json.loads(line) for line in (ROOT / 'results.jsonl').read_text().splitlines()]
    prior = json.loads((ROOT.parent / '2026-10-30-gpt-5.4-mini/manifest.json').read_text())
    assert canonical_hash(cases) == manifest['cases_sha256'] == prior['cases_sha256']
    assert canonical_hash(gold) == manifest['gold_sha256'] == prior['gold_sha256']
    assert {k: canonical_hash(v) for k, v in prompts.items()} == manifest['prompt_sha256'] == prior['prompt_sha256']
    assert manifest['model_requested'] == 'gpt-5.3-codex'
    assert manifest['max_output_tokens_per_call'] == 1200
    assert manifest['commit'] == review['source_commit']
    assert manifest['planned_calls'] == len(manifest['call_order']) == 32
    assert len(rows) == manifest['attempted_calls']
    assert sum('response' in r for r in rows) == manifest['completed_calls']
    assert [[r['case_id'], r['variant']] for r in rows] == manifest['call_order'][:len(rows)]
    assert len({(r['case_id'], r['variant']) for r in rows}) == len(rows)
    case_map = {c['case_id']: c for c in cases}
    for row in rows:
        case = case_map[row['case_id']]
        request = request_payload(manifest['model_requested'], prompts[row['variant']], case, 1200)
        assert canonical_hash(request) == row['request_sha256']
        if 'response' not in row:
            assert row['status'] == 'api_error'
            continue
        response = row['response']
        assert response['usage']['total_tokens'] == response['usage']['input_tokens'] + response['usage']['output_tokens']
        answer = None
        if response['status'] == 'completed':
            try:
                answer = json.loads(response['text'])
            except (ValueError, TypeError):
                pass
        assert answer == row['answer']
        assert score(answer, case, gold[row['case_id']]) == row['score']
        assert row['status'] == ('scored' if row['score']['valid'] else 'invalid_output')
    assert summarize(rows) == load('summary.json')
    assert calculate(rows, gold) == review['variants']
    total = sum(Decimal(x['estimated_usd']) for x in review['variants'].values())
    assert total == Decimal(review['total_estimated_usd'])
    assert sorted({r['response']['returned_model'] for r in rows if 'response' in r}) == review['provider_returned_models']
    print(f'PASS: hashes, {len(rows)} request records, saved parsing, scores, summaries and cost arithmetic; no inference.')


if __name__ == '__main__':
    main()
