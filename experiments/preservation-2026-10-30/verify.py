"""Verify the four-model preservation checkpoint without network access. Apache-2.0.

This checks preserved bytes and aggregate arithmetic; it does not authenticate
provider identity, certify benchmark labels, or independently judge model prose.
"""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def child(root, name):
    path = PurePosixPath(name)
    require(bool(path.parts) and not path.is_absolute() and '..' not in path.parts
            and '\\' not in name, 'Unsafe archive path: ' + name)
    target = root.joinpath(*path.parts)
    require(target.resolve().is_relative_to(root.resolve()), 'Path escapes repository: ' + name)
    return target


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def derive(root, entry):
    folder = child(root, entry['directory'])
    manifest = read_json(folder / 'manifest.json')
    rows = [json.loads(line) for line in (folder / 'results.jsonl').read_text(encoding='utf-8').splitlines()]
    cases, gold, prompts = [read_json(folder / (name + '.json')) for name in ('cases', 'gold', 'prompts')]
    require(canonical_hash(cases) == manifest['cases_sha256'], 'Case digest mismatch')
    require(canonical_hash(gold) == manifest['gold_sha256'], 'Gold digest mismatch')
    require({k: canonical_hash(v) for k, v in prompts.items()} == manifest['prompt_sha256'], 'Prompt digest mismatch')
    require(len(rows) == manifest['planned_calls'] == manifest['attempted_calls']
            == manifest['completed_calls'] == 32, 'Expected 32 preserved responses per model')
    require(manifest['dry_run'] is False and manifest['retries'] == 0, 'Unexpected run mode/retries')
    require(manifest['working_tree_dirty'] is False, 'Unexpected source working tree state')
    require([[r['case_id'], r['variant']] for r in rows] == manifest['call_order'], 'Call order mismatch')
    pairs = {(c['case_id'], v) for c in cases for v in ('baseline', 'receipts')}
    require(len(cases) == 16 and len(pairs) == 32 and
            {(r['case_id'], r['variant']) for r in rows} == pairs, 'Missing or duplicate case/prompt pair')
    rates = {k: Decimal(v) for k, v in entry['usd_per_million_tokens'].items()}
    variants = {}
    for name in ('baseline', 'receipts'):
        selected = [r for r in rows if r['variant'] == name]
        for row in selected:
            response = row['response']
            require(response['status'] == 'completed', 'Unexpected incomplete response')
            require(json.loads(response['text']) == row['answer'], 'Saved answer differs from response text')
            require(row['status'] == ('scored' if row['score']['valid'] else 'invalid_output'), 'Status mismatch')
            require(response['usage']['total_tokens'] == response['usage']['input_tokens'] + response['usage']['output_tokens'], 'Token arithmetic mismatch')
            require(row['score']['verdict_correct'] == (row['score']['valid'] and row['answer']['verdict'] == gold[row['case_id']]['verdict']), 'Verdict count mismatch')
        usage = [r['response']['usage'] for r in selected]
        summary = {
            'attempted': len(selected), 'api_errors': 0,
            'invalid_outputs': sum(not r['score']['valid'] for r in selected),
            'verdict_correct': sum(r['score']['verdict_correct'] for r in selected),
            'accuracy_over_all_attempts': sum(r['score']['verdict_correct'] for r in selected) / len(selected),
        }
        for key in ('unsupported_support', 'unnecessary_abstention', 'required_citations_present', 'required_limitations_present'):
            summary[key] = sum(r['score'][key] for r in selected)
        totals = {k: sum(u[k] for u in usage) for k in ('input_tokens', 'output_tokens', 'total_tokens')}
        totals['cached_input_tokens'] = sum(u['input_tokens_details']['cached_tokens'] for u in usage)
        totals['reasoning_tokens'] = sum(u['output_tokens_details']['reasoning_tokens'] for u in usage)
        totals['estimated_usd'] = str((Decimal(totals['input_tokens'] - totals['cached_input_tokens']) * rates['uncached_input']
                                      + Decimal(totals['cached_input_tokens']) * rates['cached_input']
                                      + Decimal(totals['output_tokens']) * rates['output']) / Decimal(1_000_000))
        variants[name] = {'summary': summary, 'usage': totals}
    require({k: v['summary'] for k, v in variants.items()} == read_json(folder / 'summary.json'), 'Saved summary mismatch')
    invalid = [{'case_id': r['case_id'], 'variant': r['variant'], 'errors': r['score']['errors']}
               for r in rows if not r['score']['valid']]
    return {
        'model_requested': manifest['model_requested'],
        'provider_returned_models': dict(sorted(Counter(r['response']['returned_model'] for r in rows).items())),
        'source_commit': manifest['commit'], 'run_status': manifest['status'],
        'started_at_utc': manifest['started_at_utc'], 'ended_at_utc': manifest['ended_at_utc'],
        'max_output_tokens_per_call': manifest['max_output_tokens_per_call'],
        'seed_for_order_only': manifest['seed_for_order_only'],
        'cases_sha256': manifest['cases_sha256'], 'gold_sha256': manifest['gold_sha256'],
        'prompt_sha256': manifest['prompt_sha256'], 'responses': len(rows),
        'variants': variants, 'invalid_outputs': invalid,
        'total_estimated_usd': str(sum(Decimal(v['usage']['estimated_usd']) for v in variants.values())),
    }


def totals(runs):
    result = {'models': len(runs), 'responses': sum(r['responses'] for r in runs)}
    for key in ('input_tokens', 'output_tokens', 'total_tokens', 'cached_input_tokens', 'reasoning_tokens'):
        result[key] = sum(v['usage'][key] for r in runs for v in r['variants'].values())
    result['invalid_outputs'] = sum(len(r['invalid_outputs']) for r in runs)
    result['api_errors'] = sum(v['summary']['api_errors'] for r in runs for v in r['variants'].values())
    result['total_estimated_usd'] = str(sum(Decimal(r['total_estimated_usd']) for r in runs))
    return result


def verify(root, archive):
    paths = [entry['path'] for entry in archive['files']]
    require(len(paths) == len(set(paths)) == archive['preserved_file_count'], 'Duplicate or missing inventory entry')
    for entry in archive['files']:
        data = child(root, entry['path']).read_bytes()
        require(len(data) == entry['size_bytes'], 'Size mismatch: ' + entry['path'])
        require(hashlib.sha256(data).hexdigest() == entry['sha256'], 'SHA-256 mismatch: ' + entry['path'])
        git_blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        require(git_blob == entry['git_blob_sha'], 'Git blob mismatch: ' + entry['path'])
    observed = []
    for entry in archive['runs']:
        result = derive(root, entry)
        require(result == entry['recorded_results'], 'Derived aggregate mismatch: ' + entry['directory'])
        observed.append(result)
    require(len(observed) == 4, 'Expected four model runs')
    for key in ('cases_sha256', 'gold_sha256', 'prompt_sha256', 'max_output_tokens_per_call', 'seed_for_order_only'):
        require(all(r[key] == observed[0][key] for r in observed), 'Cross-model input/configuration mismatch: ' + key)
    require(totals(observed) == archive['totals'], 'Combined totals mismatch')
    require(archive['totals']['responses'] == 128 and archive['totals']['invalid_outputs'] == 1,
            'Historical response count or retained failure changed')
    return len(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=HERE.parents[1])
    args = parser.parse_args()
    try:
        archive = read_json(child(args.root, 'experiments/preservation-2026-10-30/manifest.json'))
        count = verify(args.root, archive)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('FAIL: ' + str(exc), file=sys.stderr)
        return 1
    print(f'PASS: {count} preserved files, four models, 128 responses, original summaries and cost arithmetic. No network or inference.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
