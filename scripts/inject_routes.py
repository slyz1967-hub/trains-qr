#!/usr/bin/env python3
"""
inject_routes.py
Injects a new compressed timetable DB into index.html and bumps the version number.

The route_db.json may contain either:
  - A single 'b64' key  (legacy single-variable format, combined all days)
  - Per-day keys: 'b64_mon', 'b64_fri', 'b64_sat', 'b64_sun'
    mapping to _TT_B64_MON, _TT_B64_FRI, _TT_B64_SAT, _TT_B64_SUN in index.html

Usage: python3 inject_routes.py --routes route_db.json --html index.html
"""

import argparse
import base64
import json
import re
import zlib

# Map from route_db.json key -> JS variable name in index.html
DAY_KEY_MAP = {
    'b64_mon': '_TT_B64_MON',
    'b64_fri': '_TT_B64_FRI',
    'b64_sat': '_TT_B64_SAT',
    'b64_sun': '_TT_B64_SUN',
}

# Single-variable aliases to try for fully-legacy route_db + index.html pairs
LEGACY_ALIASES = ['_TT_B64', '_TTDB', 'TT_B64', 'TIMETABLE_B64', '_TT_DATA']


def make_pattern(var_name):
    """Return a regex that matches `var_name = 'VALUE';` (single or double quotes)."""
    return re.compile(rf"{re.escape(var_name)}\s*=\s*(['\"])([^'\"]+)\1\s*;")


def replace_var(html, var_name, new_value):
    """Replace the value of var_name in html. Returns (new_html, old_value)."""
    pattern = make_pattern(var_name)
    m = pattern.search(html)
    if not m:
        candidates = re.findall(r'(\w+)\s*=\s*[\'"]([A-Za-z0-9+/=]{40,})[\'"]', html)
        names = [c[0] for c in candidates] if candidates else ['(none found)']
        raise ValueError(
            f'Could not find variable "{var_name}" in index.html.\n'
            f'Long base64-like assignments present: {names}'
        )
    old_value = m.group(2)
    quote = m.group(1)
    new_html = pattern.sub(f"{var_name} = {quote}{new_value}{quote};", html, count=1)
    return new_html, old_value


def inject(routes_path, html_path):
    with open(routes_path) as f:
        route_data = json.load(f)
    counts = route_data.get('counts', {})

    with open(html_path, encoding='utf-8') as f:
        html = f.read()

    # ── Determine which variables to update ───────────────────────────────────
    updates = []  # list of (json_key, js_var_name, new_b64)

    day_keys = [k for k in DAY_KEY_MAP if k in route_data]

    if day_keys:
        # Normal case: route_db.json already has per-day keys
        for key in sorted(day_keys):
            updates.append((key, DAY_KEY_MAP[key], route_data[key]))

    elif 'b64' in route_data:
        new_b64 = route_data['b64']
        html_has_day_vars = any(make_pattern(v).search(html) for v in DAY_KEY_MAP.values())

        if html_has_day_vars:
            # Transitional case: old combined route_db.json + new per-day index.html.
            # Decompress the blob, split by day, re-compress each day separately.
            print('Legacy combined b64 detected with per-day HTML variables.')
            print('Decompressing and splitting into per-day blobs...')
            tt_all = json.loads(zlib.decompress(base64.b64decode(new_b64)))
            day_name_map = {'mon': '_TT_B64_MON', 'fri': '_TT_B64_FRI',
                            'sat': '_TT_B64_SAT', 'sun': '_TT_B64_SUN'}
            for day, var_name in sorted(day_name_map.items()):
                if day not in tt_all:
                    print(f'  WARNING: no "{day}" data in combined blob — skipping {var_name}')
                    continue
                day_json = json.dumps(tt_all[day], separators=(',', ':'))
                day_b64 = base64.b64encode(zlib.compress(day_json.encode(), level=9)).decode()
                updates.append((f'b64_{day}', var_name, day_b64))
                print(f'  {var_name}: {len(day_b64)} b64 chars')
        else:
            # Fully legacy: HTML also has a single combined variable
            found_alias = None
            for alias in LEGACY_ALIASES:
                if make_pattern(alias).search(html):
                    found_alias = alias
                    break
            if not found_alias:
                candidates = re.findall(r'(\w+)\s*=\s*[\'"]([A-Za-z0-9+/=]{40,})[\'"]', html)
                names = [c[0] for c in candidates] if candidates else ['(none found)']
                raise ValueError(
                    f'route_db.json has a single "b64" key but no known variable was found in index.html.\n'
                    f'Long base64-like assignments present: {names}\n'
                    f'Add the correct variable name to LEGACY_ALIASES in inject_routes.py.'
                )
            updates.append(('b64', found_alias, new_b64))
    else:
        raise ValueError(
            'route_db.json contains neither "b64" nor any per-day key '
            f'(expected one of: {list(DAY_KEY_MAP.keys())}).'
        )

    # ── Apply updates ─────────────────────────────────────────────────────────
    any_changed = False
    for json_key, var_name, new_b64 in updates:
        html, old_b64 = replace_var(html, var_name, new_b64)
        if old_b64 == new_b64:
            print(f'{var_name}: unchanged')
        else:
            print(f'{var_name}: replaced (old={len(old_b64)}, new={len(new_b64)} chars)')
            any_changed = True

    if not any_changed:
        print('All timetable data unchanged — no injection needed.')
        return False

    for d, c in counts.items():
        print(f'  {d}: {c} trains')

    # ── Update feed end date ──────────────────────────────────────────────────
    feed_end = route_data.get('feed_end')
    if feed_end:
        html = re.sub(
            r"const _TT_FEED_END = '[^']*';",
            f"const _TT_FEED_END = '{feed_end}'; // Update when new GTFS loaded — format YYYYMMDD",
            html
        )
        print(f'Feed end date updated to {feed_end}')

    # ── Bump version number ───────────────────────────────────────────────────
    ver_match = re.search(r'<!--TRAINS_VERSION:(\d+)-->', html)
    if not ver_match:
        raise ValueError('Could not find TRAINS_VERSION comment in index.html')
    old_ver = ver_match.group(1)
    new_ver = str(int(old_ver) + 1)

    html = html.replace(f'<!--TRAINS_VERSION:{old_ver}-->', f'<!--TRAINS_VERSION:{new_ver}-->')
    html = html.replace(f"var CURRENT_VERSION = '{old_ver}';", f"var CURRENT_VERSION = '{new_ver}';")
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
