#!/usr/bin/env python3
"""
inject_routes.py
Injects new per-day compressed timetable blobs into index.html and bumps the version number.

Usage: python3 inject_routes.py --routes route_db.json --html index.html
"""

import argparse
import json
import re

DAY_VARS = {
    'mon': '_TT_B64_MON',
    'fri': '_TT_B64_FRI',
    'sat': '_TT_B64_SAT',
    'sun': '_TT_B64_SUN',
}

def inject(routes_path, html_path):
    # Load the new route DB
    with open(routes_path) as f:
        route_data = json.load(f)

    days = route_data.get('days', {})
    counts = route_data.get('counts', {})

    if not days:
        print('No day data found in route_db.json')
        return False

    # Load index.html
    with open(html_path, encoding='utf-8') as f:
        html = f.read()

    changed = False

    for day, var in DAY_VARS.items():
        new_b64 = days.get(day)
        if not new_b64:
            print(f'  No data for {day}, skipping')
            continue

        pattern = rf"{var} = '([^']+)';"
        match = re.search(pattern, html)
        if not match:
            print(f'  Could not find {var} in index.html, skipping')
            continue

        old_b64 = match.group(1)
        if old_b64 == new_b64:
            print(f'  {day}: unchanged')
            continue

        html = html.replace(
            f"{var} = '{old_b64}';",
            f"{var} = '{new_b64}';"
        )
        print(f'  {day}: updated ({len(old_b64)} -> {len(new_b64)} chars)')
        changed = True

    if not changed:
        print('Timetable data unchanged — no injection needed.')
        return False

    # Update feed end date if present
    feed_end = route_data.get('feed_end')
    if feed_end:
        html = re.sub(
            r"const _TT_FEED_END = '[^']*';",
            f"const _TT_FEED_END = '{feed_end}';",
            html
        )
        print(f'Feed end date updated to {feed_end}')

    # Bump version number
    ver_match = re.search(r'<!--TRAINS_VERSION:(\d+)-->', html)
    if not ver_match:
        raise ValueError('Could not find TRAINS_VERSION comment in index.html')
    old_ver = ver_match.group(1)
    new_ver = str(int(old_ver) + 1)

    html = html.replace(
        f'<!--TRAINS_VERSION:{old_ver}-->',
        f'<!--TRAINS_VERSION:{new_ver}-->'
    )
    html = html.replace(
        f"var CURRENT_VERSION = '{old_ver}';",
        f"var CURRENT_VERSION = '{new_ver}';"
    )
    print(f'Version bumped: {old_ver} -> {new_ver}')

    # Write updated index.html
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'index.html updated successfully')
    return True

def main():
    parser = argparse.ArgumentParser(description='Inject GTFS timetable DB into TRAINS app')
    parser.add_argument('--routes', required=True, help='Path to route_db.json from build_routes.py')
    parser.add_argument('--html', default='index.html', help='Path to index.html')
    args = parser.parse_args()
    inject(args.routes, args.html)

if __name__ == '__main__':
    main()
