#!/usr/bin/env python3
"""One approved synthetic campaign; frozen prompt replay, never production routing."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glimmer_trial_preflight import (
    ARTIFACT_SHA256,
    BILLABLE_OUTPUT_BOUND,
    CEILING,
    CONTEXT_LIMIT,
    FEE_MULTIPLIER,
    INPUT_RATE,
    MODEL,
    OUTPUT_LIMIT,
    OUTPUT_RATE,
    PROVIDER,
    load_requests,
    reservation,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'evals/results/teaching-glimmer-fixed-20261012.json'
JOURNAL = ROOT / 'data/evals/glimmer-approved-20261012.sqlite3'
API = 'https://openrouter.ai/api/v1'


class Journal:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=5)
        self.db.execute('PRAGMA synchronous=FULL')
        with self.db:
            self.db.execute('CREATE TABLE IF NOT EXISTS campaign (id TEXT PRIMARY KEY)')
            self.db.execute('''CREATE TABLE IF NOT EXISTS attempt (
                name TEXT PRIMARY KEY, state TEXT NOT NULL, charge TEXT NOT NULL,
                result TEXT)''')
            identity = ARTIFACT_SHA256 + ':' + str(CEILING) + ':' + str(reservation())
            prior = self.db.execute('SELECT id FROM campaign').fetchall()
            if prior and prior != [(identity,)]:
                raise ValueError('Campaign configuration changed')
            if not prior:
                self.db.execute('INSERT INTO campaign VALUES (?)', (identity,))

    def reserve(self, name: str) -> bool:
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            rows = self.db.execute('SELECT name,state,charge FROM attempt').fetchall()
            if any(row[1] != 'settled' for row in rows):
                raise ValueError('Uncertain prior request: manual reconciliation required')
            if any(row[0] == name for row in rows):
                return False
            spent = sum((Decimal(row[2]) for row in rows), Decimal(0))
            if len(rows) >= 8 or spent + reservation() > CEILING:
                raise ValueError('Campaign allowance exhausted')
            self.db.execute('INSERT INTO attempt VALUES (?, ?, ?, NULL)',
                            (name, 'pending', str(reservation())))
        return True  # committed before a network request can start

    def settle(self, name: str, result: dict[str, Any]) -> None:
        cost = result.get('cost_usd')
        charge = reservation()
        state = 'halted'
        if cost is not None:
            actual = Decimal(str(cost))
            if actual.is_finite() and actual >= 0:
                charge = actual * FEE_MULTIPLIER
                if charge <= reservation() and result.get('accounting_valid') is True:
                    state = 'settled'
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            updated = self.db.execute(
                'UPDATE attempt SET state=?,charge=?,result=? WHERE name=? AND state=?',
                (state, str(charge), json.dumps(result), name, 'pending'),
            )
            if updated.rowcount != 1:
                raise ValueError('No matching pending attempt')

    def report(self) -> dict[str, Any]:
        rows = self.db.execute('SELECT name,state,charge,result FROM attempt ORDER BY rowid').fetchall()
        return {
            'synthetic': True, 'scope': 'frozen app prompt replay; not app-path integration',
            'artifact_sha256': ARTIFACT_SHA256, 'model': MODEL, 'provider': PROVIDER,
            'ceiling_usd': str(CEILING),
            'accounted_with_fee_usd': str(sum((Decimal(r[2]) for r in rows), Decimal(0))),
            'results': [{'case': r[0], 'state': r[1], 'reserved_or_charged_usd': r[2],
                         'response': json.loads(r[3]) if r[3] else None} for r in rows],
        }


def validate_catalog(payload: dict[str, Any]) -> None:
    data = payload['data']
    if data['id'] != MODEL:
        raise ValueError('Unexpected model')
    selected = [e for e in data['endpoints'] if e.get('tag') == PROVIDER]
    if len(selected) != 1:
        raise ValueError('Pinned endpoint unavailable')
    item = selected[0]
    prices = item['pricing']
    if (item['status'] != 0 or item['context_length'] != CONTEXT_LIMIT
            or item['max_completion_tokens'] != BILLABLE_OUTPUT_BOUND
            or not {'max_tokens', 'temperature'} <= set(item['supported_parameters'])
            or Decimal(prices['prompt']) != INPUT_RATE
            or Decimal(prices['completion']) != OUTPUT_RATE
            or Decimal(str(prices.get('request', '0'))) != 0):
        raise ValueError('Endpoint contract changed; do not spend')


async def stream_reply(client: httpx.AsyncClient, body: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    text = ''
    first = None
    usage = None
    finish = None
    provider = None
    model = None
    done = False
    async with client.stream('POST', API + '/chat/completions', json=body) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line or line.startswith(':'):
                continue
            if not line.startswith('data: '):
                raise ValueError('Unsupported stream event')
            data = line[6:]
            if data == '[DONE]':
                done = True
                break
            chunk = json.loads(data)
            if 'error' in chunk:
                raise ValueError('Provider stream error')
            for key, expected in [('provider', 'DeepInfra'), ('model', MODEL)]:
                if key in chunk and chunk[key] != expected:
                    raise ValueError('Unexpected response identity')
            provider = chunk.get('provider', provider)
            model = chunk.get('model', model)
            if chunk.get('usage') is not None:
                if usage is not None:
                    raise ValueError('Repeated usage')
                usage = chunk['usage']
            for choice in chunk.get('choices', []):
                delta = choice.get('delta', {}).get('content') or ''
                if not isinstance(delta, str):
                    raise TypeError('Non-text content')
                text += delta
                if first is None and text.strip():
                    first = time.perf_counter() - started
                finish = choice.get('finish_reason') or finish
    if not done or provider != 'DeepInfra' or model != MODEL or not isinstance(usage, dict):
        raise ValueError('Incomplete stream or missing identity/accounting')
    cost = Decimal(str(usage.get('cost')))
    tokens_in = usage.get('prompt_tokens')
    tokens_out = usage.get('completion_tokens')
    if (not cost.is_finite() or cost < 0
            or type(tokens_in) is not int or not 0 <= tokens_in <= CONTEXT_LIMIT
            or type(tokens_out) is not int or not 0 <= tokens_out <= OUTPUT_LIMIT
            or finish not in {'stop', 'length'}):
        raise ValueError('Invalid billing or completion limits')
    reasoning = (usage.get('completion_tokens_details') or {}).get('reasoning_tokens')
    warning = None
    if reasoning is not None and (type(reasoning) is not int or not 0 <= reasoning <= tokens_out):
        warning = 'inconsistent_reasoning_breakdown'
    return {
        'text': text, 'finish_reason': finish,
        'status': 'completed' if finish == 'stop' and text.strip() else 'incomplete',
        'first_visible_seconds': first, 'total_seconds': time.perf_counter() - started,
        'tokens_in': tokens_in, 'tokens_out': tokens_out,
        'reasoning_tokens': reasoning,
        'usage_detail_warning': warning,
        'cached_tokens': (usage.get('prompt_tokens_details') or {}).get('cached_tokens'),
        'cost_usd': str(cost), 'accounting_valid': True,
        'provider': provider, 'model': model, 'semantic_review': 'not_reviewed',
    }


async def run() -> None:
    requests = load_requests(SOURCE)
    key = os.environ.get('OPENROUTER_API_KEY') or dotenv_values(ROOT / '.env').get('OPENROUTER_API_KEY')
    if not key:
        raise ValueError('OPENROUTER_API_KEY is missing')
    journal = Journal(JOURNAL)
    try:
        async with httpx.AsyncClient(
            headers={'Authorization': 'Bearer ' + key}, timeout=30,
            follow_redirects=False, trust_env=False,
        ) as client:
            catalog = await client.get(API + '/models/' + MODEL + '/endpoints')
            catalog.raise_for_status()
            validate_catalog(catalog.json())
            for case in requests:
                if not journal.reserve(case['case']):
                    continue
                body = case['body']
                body['provider']['max_price'] = {'prompt': 0.3, 'completion': 1.2, 'request': 0}
                try:
                    result = await asyncio.wait_for(stream_reply(client, body), timeout=90)
                except Exception as exc:  # noqa: BLE001 — halt, no raw provider errors or retries
                    result = {'status': 'failed', 'error_type': type(exc).__name__,
                              'accounting_valid': False, 'cost_usd': None}
                result['messages_sha256'] = case['messages_sha256']
                journal.settle(case['case'], result)
                print(json.dumps({'case': case['case'], 'status': result['status']}), flush=True)
                if result.get('accounting_valid') is not True:
                    break
    finally:
        print(json.dumps(journal.report(), indent=2))
        journal.db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-approved-trial', action='store_true')
    args = parser.parse_args()
    if not args.execute_approved_trial:
        parser.error('Explicit --execute-approved-trial required; this can incur approved charges')
    try:
        asyncio.run(run())
    except Exception as error:  # noqa: BLE001 — redact credentials from errors
        print('Trial stopped: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(1) from None
