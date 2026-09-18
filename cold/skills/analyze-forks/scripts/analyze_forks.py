#!/usr/bin/env python3
"""
analyze_forks.py — Analyze a GitHub repo's fork ecosystem and PR patterns.

Usage:
    python3 analyze_forks.py owner/repo
    python3 analyze_forks.py owner/repo --max-fork-age 365
    python3 analyze_forks.py owner/repo --top-forks 50 --top-prs 30

Requires: gh CLI (authenticated)
Output: JSON to stdout, progress to stderr
"""

import subprocess
import json
import sys
import os
import argparse

# Force UTF-8 on Windows (avoid cp950 encoding errors)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'
from datetime import datetime, timezone, timedelta


# --- Filters ---

BOT_LOGINS = {
    'dependabot[bot]', 'renovate[bot]', 'greenkeeper[bot]',
    'snyk-bot', 'imgbot[bot]', 'codecov[bot]', 'github-actions[bot]',
    'stale[bot]', 'allcontributors[bot]', 'mergify[bot]', 'netlify[bot]',
    'vercel[bot]', 'pre-commit-ci[bot]', 'release-please[bot]',
    'dependabot', 'renovate',
}

TRIVIAL_PR_PATTERNS = [
    'bump ', 'chore(deps)', 'chore: bump', 'update dependency',
    'upgrade dependency', 'auto-update', 'automerge', 'chore: update',
    'chore(deps-dev)', 'build(deps)',
]


# --- GitHub API ---

def gh_api(endpoint):
    """Call gh api (GET) and return parsed JSON."""
    cmd = ["gh", "api", endpoint, "-H", "Accept: application/vnd.github+json"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def gh_search(query, sort="comments", order="desc", per_page=100):
    """Search issues/PRs with proper parameter encoding via gh -f flags."""
    cmd = [
        "gh", "api", "search/issues",
        "--method", "GET",
        "-f", f"q={query}",
        "-f", f"sort={sort}",
        "-f", f"order={order}",
        "-f", f"per_page={per_page}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        return {'items': [], 'total_count': 0}
    return json.loads(result.stdout)


# --- Fork Analysis ---

def fetch_all_forks(owner, repo, total_expected=0):
    """Fetch all forks with manual pagination and progress."""
    all_forks = []
    page = 1
    while True:
        if total_expected:
            pct = f" ({len(all_forks)}/{total_expected})"
        else:
            pct = ""
        print(f"  Fetching forks page {page}{pct}...", file=sys.stderr)

        url = f"repos/{owner}/{repo}/forks?sort=newest&per_page=100&page={page}"
        forks = gh_api(url)
        if not forks:
            break
        all_forks.extend(forks)
        if len(forks) < 100:
            break
        page += 1

    return all_forks


def filter_forks(forks, original_name, max_age_days):
    """Remove same-name forks and inactive ones. Keep all that have signal."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    results = []

    for f in forks:
        # Same name = likely just a backup/mirror
        if f['name'] == original_name:
            continue

        pushed = datetime.fromisoformat(f['pushed_at'].replace('Z', '+00:00'))
        stars = f.get('stargazers_count', 0)

        # Skip if both old AND no stars
        if pushed < cutoff and stars == 0:
            continue

        results.append({
            'full_name': f['full_name'],
            'name': f['name'],
            'description': f.get('description') or '',
            'stars': stars,
            'pushed_at': f['pushed_at'][:10],
            'html_url': f['html_url'],
            'owner_type': f['owner']['type'],
        })

    # Stars first, then recency
    results.sort(key=lambda x: (x['stars'], x['pushed_at']), reverse=True)
    return results


# --- Deep Dive: Forks ---

def deep_dive_forks(forks, top_n):
    """For top N forks, fetch recent commits to understand what they actually built."""
    if top_n == 0:
        return
    count = min(top_n, len(forks))
    print(f"\nDeep-diving top {count} forks...", file=sys.stderr)

    for i in range(count):
        fork = forks[i]
        full = fork['full_name']
        print(f"  [{i+1}/{count}] {full}...", file=sys.stderr)

        # Fetch recent commits
        commits = gh_api(f"repos/{full}/commits?per_page=10")
        if commits and isinstance(commits, list):
            fork['recent_commits'] = [
                {
                    'message': c['commit']['message'].split('\n')[0][:120],
                    'date': c['commit']['committer']['date'][:10],
                    'author': c['commit']['author']['name'],
                }
                for c in commits[:10]
            ]
        else:
            fork['recent_commits'] = []

        # Fetch repo topics (tags that describe the project)
        topics_data = gh_api(f"repos/{full}/topics")
        if topics_data and 'names' in topics_data:
            fork['topics'] = topics_data['names']
        else:
            fork['topics'] = []

    print(f"  Fork deep-dive complete.\n", file=sys.stderr)


# --- Deep Dive: PRs ---

def deep_dive_prs(owner, repo, prs, top_n):
    """For top N PRs, fetch body, diff stats, and files changed."""
    if top_n == 0:
        return
    count = min(top_n, len(prs))
    print(f"Deep-diving top {count} PRs...", file=sys.stderr)

    for i in range(count):
        pr = prs[i]
        num = pr['number']
        print(f"  [{i+1}/{count}] #{num} {pr['title'][:50]}...", file=sys.stderr)

        # Fetch full PR detail (includes body, diff stats)
        detail = gh_api(f"repos/{owner}/{repo}/pulls/{num}")
        if detail:
            body = detail.get('body') or ''
            # Truncate body but keep enough for meaningful analysis
            pr['body'] = body[:800] if len(body) > 800 else body
            pr['additions'] = detail.get('additions', 0)
            pr['deletions'] = detail.get('deletions', 0)
            pr['changed_files'] = detail.get('changed_files', 0)
            pr['merged'] = detail.get('merged', False)

        # Fetch files changed (just names, not full diffs)
        files = gh_api(f"repos/{owner}/{repo}/pulls/{num}/files")
        if files and isinstance(files, list):
            pr['files'] = [
                {
                    'filename': f['filename'],
                    'changes': f.get('changes', 0),
                    'status': f.get('status', ''),
                }
                for f in files[:20]  # Cap at 20 files
            ]
        else:
            pr['files'] = []

    print(f"  PR deep-dive complete.\n", file=sys.stderr)


# --- PR Analysis ---

def is_bot(item):
    """Check if a PR author is a bot."""
    login = item['user']['login'].lower()
    return login in BOT_LOGINS or item['user'].get('type') == 'Bot'


def is_trivial(title):
    """Check if a PR title indicates a trivial/automated change."""
    t = title.lower()
    return any(p in t for p in TRIVIAL_PR_PATTERNS)


def fetch_prs(owner, repo):
    """Fetch interesting PRs using GitHub Search API."""
    prs = []
    seen = set()

    searches = [
        (f"repo:{owner}/{repo} is:pr comments:>=3", "Most discussed PRs"),
        (f"repo:{owner}/{repo} is:pr is:open", "Open PRs"),
    ]

    for query, label in searches:
        print(f"  Searching: {label}...", file=sys.stderr)
        result = gh_search(query)

        for item in result.get('items', []):
            num = item['number']
            if num in seen:
                continue
            seen.add(num)

            if is_bot(item) or is_trivial(item['title']):
                continue

            merged = bool(item.get('pull_request', {}).get('merged_at'))
            prs.append({
                'number': num,
                'title': item['title'],
                'user': item['user']['login'],
                'state': 'merged' if merged else item['state'],
                'comments': item.get('comments', 0),
                'labels': [l['name'] for l in item.get('labels', [])],
                'created_at': item['created_at'][:10],
                'html_url': item['html_url'],
            })

    prs.sort(key=lambda x: x['comments'], reverse=True)
    return prs


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description='Analyze a GitHub repo fork ecosystem and PR patterns'
    )
    parser.add_argument('repo', help='owner/repo (e.g. anthropics/claude-code)')
    parser.add_argument(
        '--max-fork-age', type=int, default=730,
        help='Only include forks pushed within N days (default: 730 = 2 years)'
    )
    parser.add_argument(
        '--top-forks', type=int, default=30,
        help='Number of top forks to deep-dive for commits/topics (default: 30)'
    )
    parser.add_argument(
        '--top-prs', type=int, default=20,
        help='Number of top PRs to deep-dive for body/files (default: 20)'
    )
    args = parser.parse_args()

    try:
        owner, repo_name = args.repo.split('/')
    except ValueError:
        print("Error: repo must be in owner/repo format", file=sys.stderr)
        sys.exit(1)

    # --- Repo info ---
    print(f"Analyzing {owner}/{repo_name}...", file=sys.stderr)
    info = gh_api(f"repos/{owner}/{repo_name}")
    if not info:
        print("Error: repo not found or not accessible", file=sys.stderr)
        sys.exit(1)

    total_forks = info.get('forks_count', 0)
    print(f"  {info['stargazers_count']} stars | {total_forks} forks\n", file=sys.stderr)

    # --- Forks ---
    print("Fetching forks...", file=sys.stderr)
    all_forks = fetch_all_forks(owner, repo_name, total_forks)
    good_forks = filter_forks(all_forks, info['name'], args.max_fork_age)

    same_name = sum(1 for f in all_forks if f['name'] == info['name'])
    renamed = len(all_forks) - same_name
    print(
        f"  {len(all_forks)} total -> {same_name} same-name removed "
        f"-> {renamed} renamed -> {len(good_forks)} interesting\n",
        file=sys.stderr
    )

    # --- PRs ---
    print("Fetching PRs...", file=sys.stderr)
    good_prs = fetch_prs(owner, repo_name)
    print(f"  {len(good_prs)} interesting PRs\n", file=sys.stderr)

    # --- Deep Dive ---
    deep_dive_forks(good_forks, args.top_forks)
    deep_dive_prs(owner, repo_name, good_prs, args.top_prs)

    # --- Output ---
    output = {
        'repo': {
            'full_name': info['full_name'],
            'description': info.get('description') or '',
            'stars': info['stargazers_count'],
            'forks_total': total_forks,
            'url': info['html_url'],
        },
        'forks': {
            'total_fetched': len(all_forks),
            'same_name_removed': same_name,
            'renamed_total': renamed,
            'interesting': len(good_forks),
            'deep_dived': min(args.top_forks, len(good_forks)),
            'items': good_forks,
        },
        'prs': {
            'interesting': len(good_prs),
            'deep_dived': min(args.top_prs, len(good_prs)),
            'items': good_prs,
        },
    }

    # Write UTF-8 bytes directly to bypass Windows cp950 encoding layer
    output_bytes = json.dumps(output, indent=2, ensure_ascii=False).encode('utf-8')
    sys.stdout.buffer.write(output_bytes)
    sys.stdout.buffer.write(b'\n')
    print(f"\nDone!", file=sys.stderr)


if __name__ == '__main__':
    main()
