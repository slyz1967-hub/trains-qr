#!/usr/bin/env python3
"""
build_routes.py
Builds a compressed timetable DB from Translink GTFS data.
Outputs a JSON file containing mon/fri/sat/sun stop times for all QR rail services.

Usage: python3 build_routes.py --gtfs ./gtfs --output route_db.json
"""

import argparse
import csv
import json
import re
import base64
import zlib
from collections import defaultdict

# ── GTFS code -> ROUTE_DB code mapping ───────────────────────────────────────
# These 13 stations use different codes in the GTFS feed vs the app's ROUTE_DB
GTFS_CODE_MAP = {
    'HLM': 'HVW',  # Holmview
    'ELG': 'EDL',  # Edens Landing
    'KSN': 'KGT',  # Kingston
    'WGE': 'WDG',  # Woodridge
    'KBY': 'KRY',  # Kuraby
    'FGV': 'FTG',  # Fruitgrove
    'BNN': 'BAN',  # Banoon
    'CPS': 'CEP',  # Coopers Plains
    'SBY': 'SLY',  # Salisbury
    'RCL': 'RKE',  # Rocklea (RCL = Richlands in ROUTE_DB — different station)
    'YRP': 'YLY',  # Yeerongpilly
    'YGA': 'YRG',  # Yeronga
    'FAF': 'FFI',  # Fairfield
}

# Station name -> ROUTE_DB code mapping (derived from app's ROUTE_DB)
# Built from the station names in the app — used to map GTFS stop names to codes
STATION_NAME_MAP = {
    'domestic airport': 'BDT',
    'international airport': 'BIT',
    'eagle junction': 'EGJ',
    'wooloowin': 'WLW',
    'albion': 'ALB',
    'bowen hills': 'BHI',
    'fortitude valley': 'FVY',
    'central': 'CTL',
    'roma street': 'RST',
    'south brisbane': 'SBE',
    'south bank': 'SBK',
    'boggo road': 'BGR',
    'dutton park': 'DTP',
    'fairfield': 'FFI',
    'yeronga': 'YRG',
    'yeerongpilly': 'YLY',
    'moorooka': 'MRK',
    'rocklea': 'RKE',
    'salisbury': 'SLY',
    'coopers plains': 'CEP',
    'banoon': 'BAN',
    'sunnybank': 'SNB',
    'altandi': 'ATI',
    'runcorn': 'RCN',
    'fruitgrove': 'FTG',
    'kuraby': 'KRY',
    'trinder park': 'TPK',
    'woodridge': 'WDG',
    'kingston': 'KGT',
    'loganlea': 'LGL',
    'bethania': 'BTI',
    'edens landing': 'EDL',
    'holmview': 'HVW',
    'beenleigh': 'BNH',
    'ormeau': 'ORM',
    'pimpama': 'PMP',
    'coomera': 'CXM',
    'helensvale': 'HLN',
    'nerang': 'NEG',
    'robina': 'ROB',
    'varsity lakes': 'VYS',
    'north boondall': 'NBD',
    'boondall': 'BDL',
    'nudgee': 'NUD',
    'banyo': 'BYO',
    'virginia': 'VGI',
    'bindha': 'BHA',
    'shorncliffe': 'SHC',
    'sandgate': 'SGE',
    'brighton': 'BRD',
    'hemmant': 'HMT',
    'wynnum north': 'WYN',
    'wynnum': 'WYH',
    'manly': 'MNY',
    'lota': 'LTA',
    'murarrie': 'MRR',
    'morningside': 'MNG',
    'cannon hill': 'CNH',
    'norman park': 'NMP',
    'hawthorne': 'HMT',
    'cleveland': 'CVN',
    'wellington point': 'WLP',
    'ormiston': 'ORO',
    'birkdale': 'BKD',
    'capalaba': 'CPO',
    'thorneside': 'TNS',
    'northgate': 'NTG',
    'virginia': 'VGI',
    'toombul': 'TBL',
    'nundah': 'NDA',
    'hendra': 'HMT',
    'doomben': 'DBN',
    'ascot': 'ALB',
    'racecourse': 'RCN',
    'exhibition': 'ENG',
    'park road': 'PKR',
    'ipswich': 'IPS',
    'north ipswich': 'NMP',
    'booval': 'BOV',
    'bundamba': 'BAN',
    'leichhardt': 'LDM',
    'western junction': 'WND',
    'dinmore': 'DNM',
    'gailes': 'GAL',
    'wacol': 'WAC',
    'darra': 'DAR',
    'oxley': 'OXP',
    'corinda': 'CND',
    'graceville': 'GRV',
    'sherwood': 'SHW',
    'chelmer': 'CHM',
    'indooroopilly': 'IRP',
    'taringa': 'TGA',
    'toowong': 'TWG',
    'auchenflower': 'ACF',
    'milton': 'MLT',
    'rosewood': 'RSW',
    'grandchester': 'GDA',
    'peak crossing': 'PKR',
    'harrisville': 'HDR',
    'amberley': 'EIP',
    'camira': 'CMR',
    'springfield central': 'SPC',
    'springfield': 'SPF',
    'richlands': 'RCL',
    'forest lake': 'FTG',
    'ferny grove': 'FYG',
    'ferny hills': 'FHI',
    'arana hills': 'ARH',
    'keperra': 'KRP',
    'gaythorne': 'GAO',
    'enoggera': 'ENG',
    'alderley': 'ADY',
    'newmarket': 'NWM',
    'wilston': 'WLQ',
    'mitchelton': 'MCH',
    'oxford park': 'OXP',
    'grovely': 'GDA',
    'keperra': 'KRP',
    'caboolture': 'CBT',
    'morayfield': 'MYE',
    'burpengary': 'BPY',
    'narangba': 'NAM',
    'dakabin': 'DKB',
    'petrie': 'PET',
    'lawnton': 'LWT',
    'bald hills': 'BDS',
    'strathpine': 'SPN',
    'brendale': 'BNH',
    'carseldine': 'CDE',
    'zillmere': 'ZLL',
    'geebung': 'GEB',
    'virginia': 'VGI',
    'kippa-ring': 'KPR',
    'kippa ring': 'KPR',
    'rothwell': 'RTW',
    'kallangur': 'KLG',
    'mango hill east': 'MJE',
    'mango hill': 'MGH',
    'nambour': 'NAM',
    'palmwoods': 'PAL',
    'woombye': 'WOB',
    'yandina': 'YDA',
    'eumundi': None,
    'cooroy': 'COO',
    'pomona': 'PMQ',
    'gympie north': 'GYN',
    'glass house mountains': 'GHM',
    'beerburrum': None,
    'beerwah': None,
    'landsborough': None,
    'mooloolah': 'MOH',
}


def to_mins(t):
    """Convert HH:MM:SS or HH:MM to minutes since midnight."""
    if not t:
        return None
    parts = t.strip().split(':')
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        return None


def build_stop_mapping(gtfs_dir):
    """Build stop_id -> ROUTE_DB station code mapping from stops.txt."""
    stop_id_to_code = {}
    with open(f'{gtfs_dir}/stops.txt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            sid = r['stop_id']
            name = r['stop_name']
            # Clean name: remove "station, platform X" suffix
            clean = re.sub(r'\s*station.*$', '', name, flags=re.IGNORECASE).strip().lower()
            clean = re.sub(r',\s*(platform|stop|gate|bay).*$', '', clean).strip()
            code = STATION_NAME_MAP.get(clean)
            if not code:
                # Try partial match for longer names
                for sname, scode in STATION_NAME_MAP.items():
                    if sname and clean and len(clean) > 4 and clean in sname:
                        code = scode
                        break
            if code:
                stop_id_to_code[sid] = code
    return stop_id_to_code


def build_timetable(gtfs_dir):
    """Build timetable DB with mon/fri/sat/sun entries."""
    print('Loading routes...')
    rail_routes = set()
    with open(f'{gtfs_dir}/routes.txt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r.get('route_type', '') == '2':
                rail_routes.add(r['route_id'])
    print(f'  {len(rail_routes)} rail routes')

    print('Loading calendar...')
    day_services = {'mon': set(), 'fri': set(), 'sat': set(), 'sun': set()}
    with open(f'{gtfs_dir}/calendar.txt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            for day, col in [('mon', 'monday'), ('fri', 'friday'),
                              ('sat', 'saturday'), ('sun', 'sunday')]:
                if r.get(col, '0') == '1':
                    day_services[day].add(r['service_id'])
    for d, s in day_services.items():
        print(f'  {d}: {len(s)} service IDs')

    print('Loading stop mapping...')
    stop_id_to_code = build_stop_mapping(gtfs_dir)
    print(f'  {len(stop_id_to_code)} stop mappings')

    print('Loading trips...')
    day_trips = {d: {} for d in day_services}
    with open(f'{gtfs_dir}/trips.txt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['route_id'] not in rail_routes:
                continue
            tid = r['trip_id']
            train_no = tid.split('-')[-1]
            sid = r['service_id']
            for day in day_services:
                if sid in day_services[day]:
                    day_trips[day][tid] = train_no
    for d, t in day_trips.items():
        unique = len(set(t.values()))
        print(f'  {d}: {len(t)} trips, {unique} unique train numbers')

    print('Loading stop times (this may take a moment)...')
    all_target_trips = set()
    for d in day_trips:
        all_target_trips.update(day_trips[d].keys())

    trip_stops = defaultdict(list)
    with open(f'{gtfs_dir}/stop_times.txt', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader):
            if i % 500000 == 0 and i > 0:
                print(f'  ...{i:,} rows processed')
            tid = r['trip_id']
            if tid not in all_target_trips:
                continue
            sid = r['stop_id']
            code = stop_id_to_code.get(sid)
            if not code:
                continue
            dep = to_mins(r['departure_time'])
            if dep is None:
                continue
            seq = int(r.get('stop_sequence', 0))
            trip_stops[tid].append((seq, dep, code))
    print(f'  Loaded stops for {len(trip_stops)} trips')

    print('Building timetable DB...')
    tt_db = {}
    for day in day_trips:
        train_trips = defaultdict(list)
        for tid, train_no in day_trips[day].items():
            train_trips[train_no].append(tid)

        tt = {}
        for train_no, tids in train_trips.items():
            # Pick the trip with most mapped stops
            best_stops = []
            for tid in tids:
                stops = sorted(trip_stops.get(tid, []))
                if len(stops) > len(best_stops):
                    best_stops = stops

            if not best_stops:
                continue

            first_mins = best_stops[0][1]
            stops_dict = {}
            for seq, dep, code in best_stops:
                if code not in stops_dict:
                    stops_dict[code] = dep - first_mins

            if len(stops_dict) >= 2:
                tt[train_no] = {'first_mins': first_mins, 'stops': stops_dict}

        tt_db[day] = tt
        print(f'  {day}: {len(tt)} trains with timetable data')

    return tt_db


def main():
    parser = argparse.ArgumentParser(description='Build GTFS timetable DB for TRAINS app')
    parser.add_argument('--gtfs', required=True, help='Path to extracted GTFS directory')
    parser.add_argument('--output', default='route_db.json', help='Output JSON file')
    args = parser.parse_args()

    tt_db = build_timetable(args.gtfs)

    # Compress and base64 encode
    json_str = json.dumps(tt_db, separators=(',', ':'))
    compressed = zlib.compress(json_str.encode(), level=9)
    b64 = base64.b64encode(compressed).decode()

    # Save as JSON with the b64 string and metadata
    output = {
        'b64': b64,
        'days': list(tt_db.keys()),
        'counts': {d: len(tt_db[d]) for d in tt_db},
    }
    with open(args.output, 'w') as f:
        json.dump(output, f)

    print(f'\nOutput written to {args.output}')
    print(f'B64 length: {len(b64)} chars')
    for d in tt_db:
        print(f'  {d}: {len(tt_db[d])} trains')


if __name__ == '__main__':
    main()
