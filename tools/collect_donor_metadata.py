#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

CFG = Path('tools/donor_sources_2026_05_04.json')
OUT = Path('docs/DONOR_METADATA_COLLECTION_REPORT_2026-05-04.md')
TOKEN = os.environ.get('GITHUB_TOKEN', '').strip()


def fetch_json(url: str):
    headers = {'User-Agent': 'aesolator-donor-metadata/1.0'}
    if TOKEN:
        headers['Authorization'] = f'Bearer {TOKEN}'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))


def fetch_text(url: str):
    headers = {'User-Agent': 'aesolator-donor-metadata/1.0'}
    if TOKEN:
        headers['Authorization'] = f'Bearer {TOKEN}'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8', errors='replace')


def collect_for(label: str, key: str):
    owner, repo = label.split('/', 1)
    result = {
        'label': label,
        'key': key,
        'local_checkout': Path('donors') / key,
        'api_repo_ok': False,
        'default_branch': '',
        'stars': None,
        'last_push': '',
        'readme_ok': False,
        'readme_head': '',
        'error': '',
    }

    if result['local_checkout'].exists():
        result['api_repo_ok'] = True

    try:
        meta = fetch_json(f'https://api.github.com/repos/{owner}/{repo}')
        result['api_repo_ok'] = True
        result['default_branch'] = meta.get('default_branch', '')
        result['stars'] = meta.get('stargazers_count')
        result['last_push'] = meta.get('pushed_at', '')
    except Exception as ex:
        result['error'] = f'api:{ex}'

    branch = result['default_branch'] or 'main'
    for candidate in [
        f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md',
        f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/readme.md',
    ]:
        try:
            text = fetch_text(candidate)
            result['readme_ok'] = True
            result['readme_head'] = '\n'.join(text.splitlines()[:3])[:180]
            break
        except Exception as ex:
            if not result['error']:
                result['error'] = f'readme:{ex}'

    return result


def main():
    donors = json.loads(CFG.read_text(encoding='utf-8')).get('donors', [])
    lines = [
        '# Donor Metadata Collection Report',
        '',
        'Updated: `2026-05-04`',
        '',
        'Collection method: local checkout probe + GitHub API repo metadata + RAW README probe.',
        ''
    ]

    for d in donors:
        r = collect_for(d['label'], d['key'])
        lines.append(f"## {r['label']}")
        lines.append(f"- key: `{r['key']}`")
        lines.append(f"- local checkout: `{r['local_checkout']}` -> `{'present' if r['local_checkout'].exists() else 'missing'}`")
        lines.append(f"- api repo metadata: `{'ok' if r['api_repo_ok'] else 'blocked'}`")
        if r['default_branch']:
            lines.append(f"- default branch: `{r['default_branch']}`")
        if r['stars'] is not None:
            lines.append(f"- stars: `{r['stars']}`")
        if r['last_push']:
            lines.append(f"- last push: `{r['last_push']}`")
        lines.append(f"- raw README probe: `{'ok' if r['readme_ok'] else 'blocked'}`")
        if r['readme_head']:
            lines.append(f"- README head: `{r['readme_head'].replace('`','')}`")
        if r['error']:
            lines.append(f"- blocker: `{r['error']}`")
        lines.append('')

    OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
