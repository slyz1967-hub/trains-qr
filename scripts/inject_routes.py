#!/usr/bin/env python3
"""
inject_routes.py
Injects a new compressed timetable DB into index.html and bumps the version number.

Usage: python3 inject_routes.py --routes route_db.json --html index.html
"""

import argparse
import json
import re


def inject(routes_path, html_path):
    # Load the new route DB
    with open(routes_path) as f:
        route_data = json.load(f)
    new_b64 = route_data['b64']
    counts = route_data.get('counts', {})

    # Load index.html
    with open(html_path, encoding='utf-8') as f:
        html = f.read()

    # ── Replace _TT_B64 ───────────────────────────────────────────────────────
    old_b64_match = re.search(r"_TT_B64 = '([^']+)';", html)
    if not old_b64_match:
        raise ValueError('Could not find _TT_B64 in index.html')
    old_b64 = old_b64_match.group(1)

    if old_b64 == new_b64:
        print('Timetable data unchanged — no injection needed.')
        return False

    html = html.replace(
        f"_TT_B64 = '{old_b64}';",
        f"_TT_B64 = '{new_b64}';"
    )
    print(f'Timetable DB replaced (old={len(old_b64)}, new={len(new_b64)} chars)')
    for d, c in counts.items():
        print(f'  {d}: {c} trains')

    # ── Bump version number ───────────────────────────────────────────────────
    # Find current version
    ver_match = re.search(r'<!--TRAINS_VERSION:(\d+)-->', html)
    if not ver_match:
        raise ValueError('Could not find TRAINS_VERSION comment in index.html')
    old_ver = ver_match.group(1)
    new_ver = str(int(old_ver) + 1)

    html = html.replace(
        f'<!--TRAINS_VERSION:{old_ver}-->',
        f'<!--TRAINS_VERSION:{new_ver}-->'
    )
    # Also update CURRENT_VERSION in both places it appears (version check script + installUpdate)
    html = html.replace(
        f"var CURRENT_VERSION = '{old_ver}';",
        f"var CURRENT_VERSION = '{new_ver}';"
    )
    print(f'Version bumped: {old_ver} -> {new_ver}')

    # ── Write updated index.html ──────────────────────────────────────────────
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'index.html updated successfully')
    return True


def main():
    parser = argparse.ArgumentParser(description='Inject GTFS timetable DB into TRAINS app')
    parser.add_argument('--routes', required=True, help='Path to route_db.json from build_routes.py')
    parser.add_argument('--html', default='index.html', help='Path to index.html')
    args = parser.parse_args()

    changed = inject(args.routes, args.html)
    exit(0 if changed else 1)


if __name__ == '__main__':
    main()
