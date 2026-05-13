#!/usr/bin/env python3
"""
inject_routes.py
Injects a new compressed timetable DB into index.html and bumps the version number.

Usage: python3 inject_routes.py --routes route_db.json --html index.html
"""

import argparse
import json
import re


# Patterns to try when locating the timetable B64 variable.
# Each is tried in order; the first match wins.
_B64_PATTERNS = [
    r"(_TT_B64)\s*=\s*'([^']+)';",      # single quotes
    r'(_TT_B64)\s*=\s*"([^"]+)";',      # double quotes
    r"(_TTDB)\s*=\s*'([^']+)';",
    r'(_TTDB)\s*=\s*"([^"]+)";',
    r"(TT_B64)\s*=\s*'([^']+)';",
    r'(TT_B64)\s*=\s*"([^"]+)";',
    r"(TIMETABLE_B64)\s*=\s*'([^']+)';",
    r'(TIMETABLE_B64)\s*=\s*"([^"]+)";',
    r"(_TT_DATA)\s*=\s*'([^']+)';",
    r'(_TT_DATA)\s*=\s*"([^"]+)";',
]


def find_b64(html):
    """Return (pattern_used, var_name, old_value) or raise with diagnostics."""
    for pattern in _B64_PATTERNS:
        m = re.search(pattern, html)
        if m:
            return pattern, m.group(1), m.group(2)

    # Nothing matched — print nearby candidates to help diagnose
    candidates = re.findall(r'(\w+)\s*=\s*[\'"]([A-Za-z0-9+/=]{40,})[\'"]', html)
    if candidates:
        names = [c[0] for c in candidates]
        raise ValueError(
            f'Could not find a known timetable B64 variable in index.html.\n'
            f'Found these long base64-like assignments: {names}\n'
            f'Add the correct variable name to _B64_PATTERNS in inject_routes.py.'
        )
    raise ValueError(
        'Could not find _TT_B64 (or any known alias) in index.html. '
        'The variable may have been renamed — check index.html and update _B64_PATTERNS.'
    )


def inject(routes_path, html_path):
    # Load the new route DB
    with open(routes_path) as f:
        route_data = json.load(f)
    new_b64 = route_data['b64']
    counts = route_data.get('counts', {})

    # Load index.html
    with open(html_path, encoding='utf-8') as f:
        html = f.read()

    # ── Replace timetable B64 ─────────────────────────────────────────────────
    pattern_used, var_name, old_b64 = find_b64(html)
    print(f'Found timetable variable: {var_name}')

    if old_b64 == new_b64:
        print('Timetable data unchanged — no injection needed.')
        return False

    # Update feed end date if present in route_db.json
    feed_end = route_data.get('feed_end')
    if feed_end:
        html = re.sub(
            r"const _TT_FEED_END = '[^']*';",
            f"const _TT_FEED_END = '{feed_end}'; // Update when new GTFS loaded — format YYYYMMDD",
            html
        )
        print(f'Feed end date updated to {feed_end}')

    # Replace old value with new, preserving the quote style used in the file
    html = re.sub(pattern_used, lambda m: m.group(0).replace(old_b64, new_b64), html, count=1)
    print(f'Timetable DB replaced (old={len(old_b64)}, new={len(new_b64)} chars)')
    for d, c in counts.items():
        print(f'  {d}: {c} trains')

    # ── Bump version number ───────────────────────────────────────────────────
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

    # ── Write updated index.html ──────────────────────────────────────────────
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print('index.html updated successfully')
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
