#!/usr/bin/env python3
"""
TRAINS Route Builder
Reads SEQ GTFS stop_times.txt + stops.txt + trips.txt
Outputs updated ROUTE_DB and station codes for index.html

Usage: python3 build_routes.py --gtfs ./gtfs_dir --out ./route_db.json
"""

import csv, json, sys, os, re, argparse, zipfile
from collections import defaultdict

# ── APP STATION CODE MAP (GTFS parent_station → app code) ────────────
GTFS_TO_APP = {
    'place_albsta': 'ALB', 'place_aldsta': 'ADY', 'place_altsta': 'ATI',
    'place_ascsta': 'ASC', 'place_aucsta': 'ACF', 'place_balsta': 'BDS',
    'place_baysta': 'BYO', 'place_bansta': 'BAN', 'place_beesta': 'BNH',
    'place_bbrsta': 'BBM', 'place_bwrsta': 'BRW', 'place_betsta': 'BTI',
    'place_binsta': 'BHA', 'place_birsta': 'BKD', 'place_parsta': 'BGR',
    'place_bvlsta': 'BOV', 'place_bowsta': 'BHI', 'place_brasta': 'BPR',
    'place_ebbsta': 'EBV', 'place_corsta': 'CND', 'place_bunsta': 'BDA',
    'place_brdsta': 'BRD', 'place_bursta': 'BPY', 'place_cabsta': 'CBT',
    'place_cassta': 'CDE', 'place_censta': 'CTL', 'place_chesta': 'CHM',
    'place_clasta': 'CLF', 'place_clesta': 'CVN', 'place_cppsta': 'CEP',
    'place_coosta': 'CPO', 'place_crnsta': 'COZ', 'place_crysta': 'COO',
    'place_daksta': 'DKB', 'place_darsta': 'DRA', 'place_deasta': 'DGN',
    'place_domsta': 'BDT', 'place_dbnsta': 'DBN', 'place_dupsta': 'DTP',
    'place_eassta': 'EIP', 'place_edesta': 'EDL', 'place_elmsta': 'ELB',
    'place_enosta': 'ENG', 'place_eudsta': 'EDO', 'place_faista': 'FFI',
    'place_yersta': 'YRG', 'place_fersta': 'FYG', 'place_forsta': 'FVY',
    'place_geesta': 'GEB', 'place_gmtsta': 'GHM', 'place_goosta': 'GDA',
    'place_grosta': 'GRV', 'place_gaysta': 'GAO', 'place_gaista': 'GAL',
    'place_hemsta': 'HMT', 'place_hensta': 'HDR', 'place_holsta': 'HVW',
    'place_helsta': 'HLN', 'place_indsta': 'IRP', 'place_intsta': 'BIT',
    'place_ipssta': 'IPS', 'place_kalsta': 'KLG', 'place_karsta': 'KRB',
    'place_kepsta': 'KPR', 'place_kgtsta': 'KGT', 'place_kprsta': 'KRP',
    'place_kursta': 'KRY', 'place_lansta': 'LBH', 'place_lawsta': 'LWT',
    'place_linsta': 'LDM', 'place_logsta': 'LGL', 'place_lotsta': 'LTA',
    'place_winsta': 'WND', 'place_mhesta': 'MJE', 'place_mahsta': 'MGH',
    'place_mansta': 'MNY', 'place_milsta': 'MLT', 'place_mitsta': 'MCH',
    'place_molsta': 'MOH', 'place_myesta': 'MYE', 'place_mursta': 'MRR',
    'place_mudsta': 'MRD', 'place_namsta': 'NAM', 'place_narsta': 'NRB',
    'place_nrgsta': 'NEG', 'place_wilsta': 'WLQ', 'place_npksta': 'NMP',
    'place_nobsta': 'NBD', 'place_nudsta': 'NUD', 'place_nunsta': 'NDA',
    'place_omesta': 'ORM', 'place_ormsta': 'ORO', 'place_oxfsta': 'OXP',
    'place_oxlsta': 'OXL', 'place_palsta': 'PAL', 'place_petsta': 'PET',
    'place_pimsta': 'PMP', 'place_pomsta': 'PMQ', 'place_sansta': 'SGE',
    'place_redsta': 'RDK', 'place_ricsta': 'RCL', 'place_dinsta': 'DNM',
    'place_rivsta': 'RVV', 'place_rbnsta': 'ROB', 'place_rocsta': 'RKE',
    'place_romsta': 'RST', 'place_rossta': 'RSW', 'place_rotsta': 'RTW',
    'place_runsta': 'RCN', 'place_slysta': 'SLY', 'place_shesta': 'SHW',
    'place_shnsta': 'SHC', 'place_sbasta': 'SBK', 'place_sousta': 'SBE',
    'place_strsta': 'SPN', 'place_spcsta': 'SPC', 'place_sprsta': 'SPF',
    'place_sunsta': 'SNB', 'place_snssta': 'SSN', 'place_tarsta': 'TRG',
    'place_thasta': 'TGA', 'place_thmsta': 'TST', 'place_thosta': 'TNS',
    'place_tomsta': 'TBL', 'place_twgsta': 'TWG', 'place_trvsta': 'TRA',
    'place_varsta': 'VYS', 'place_virsta': 'VGI', 'place_walsta': 'WLN',
    'place_welsta': 'WLP', 'place_wacsta': 'WAC', 'place_newsta': 'NWM',
    'place_wdrsta': 'WDG', 'place_wolsta': 'WLW', 'place_wbysta': 'WOB',
    'place_wulsta': 'WKK', 'place_wyhsta': 'WYH', 'place_mgssta': 'MNG',
    'place_wnmsta': 'WYN', 'place_yansta': 'YDA', 'place_yeesta': 'YLY',
    'place_zllsta': 'ZLL', 'place_egjsta': 'EGJ', 'place_bdlsta': 'BDL',
    'place_frusta': 'FTG', 'place_grasta': 'GVL', 'place_cansta': 'CNH',
    'place_norsta': 'NTG', 'place_moosta': 'MRK', 'place_wynsta': 'WYC',
    'place_gymsta': 'GYN', 'place_sgtsta': 'SGE',
    # Gold Coast tram - not used in TRAINS
    'place_cavsta': None, 'place_cypsta': None, 'place_nlksta': None,
    'place_vptsta': None,
}

# ── ROUTE DEFINITIONS (GTFS route_id prefix → app route key) ─────────
# Maps GTFS route patterns to the ROUTE_DB keys used in the app
ROUTE_MAP = {
    # Beenleigh line
    'RWIP': 'IPW',      # Ipswich/Rosewood all stations
    'RPIP': 'IPW',      # Ipswich peak
    'RPSP': 'SPF',      # Springfield
    'RWRP': 'KPR',      # Kippa-Ring
    'RWCA': 'CBT',      # Caboolture
    'RWNA': 'CBT',      # Nambour (via Caboolture)
    'RWBR': 'BNL',      # Beenleigh
    'RPBR': 'BNL',      # Beenleigh peak
    'RPSH': 'SHC',      # Shorncliffe
    'R609': 'CBT',      # Caboolture/Ipswich cross-city
    'R610': 'CBT',      # Caboolture/Nambour
    'R612': 'CBT',      # Gympie North
}

def parse_time(t):
    """Parse GTFS time HH:MM:SS to minutes from midnight"""
    try:
        h, m, s = t.strip().split(':')
        return int(h) * 60 + int(m)
    except:
        return None

def load_stops(gtfs_dir):
    """Load stop_id → {parent, name} mapping"""
    stops = {}
    path = os.path.join(gtfs_dir, 'stops.txt')
    with open(path, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            stops[row['stop_id'].strip()] = {
                'parent': row.get('parent_station','').strip(),
                'name': row.get('stop_name','').strip(),
                'code': GTFS_TO_APP.get(row.get('parent_station','').strip())
            }
    return stops

def load_rail_trips(gtfs_dir):
    """Load trip_id → {route_id, headsign, service_id} for rail only"""
    trips = {}
    path = os.path.join(gtfs_dir, 'trips.txt')
    with open(path, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            rid = row['route_id'].strip()
            if rid.startswith('R'):
                trips[row['trip_id'].strip()] = {
                    'route_id': rid,
                    'headsign': row.get('trip_headsign','').strip(),
                    'service_id': row.get('service_id','').strip(),
                    'direction': row.get('direction_id','0').strip(),
                }
    return trips

def build_route_sequences(gtfs_dir, stops, trips):
    """
    Read stop_times.txt and build stop sequences per route.
    Returns dict: route_key → list of app_station_codes in order
    """
    route_sequences = defaultdict(lambda: defaultdict(list))
    # trip_id → sorted list of (stop_sequence, app_code, departure_mins)
    trip_stops = defaultdict(list)

    path = os.path.join(gtfs_dir, 'stop_times.txt')
    print("Reading stop_times.txt (this may take a moment)...")
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            trip_id = row['trip_id'].strip()
            if trip_id not in trips:
                continue  # not a rail trip
            stop_id = row['stop_id'].strip()
            stop_info = stops.get(stop_id, {})
            app_code = stop_info.get('code')
            if not app_code:
                continue  # unmapped stop
            seq = int(row.get('stop_sequence', 0))
            dep = parse_time(row.get('departure_time', ''))
            trip_stops[trip_id].append((seq, app_code, dep))
            if i % 500000 == 0:
                print(f"  ...{i:,} rows processed")

    print(f"Building route sequences from {len(trip_stops)} rail trips...")

    # For each trip, build ordered stop sequence and accumulate per route
    route_trip_seqs = defaultdict(list)
    for trip_id, stop_list in trip_stops.items():
        stop_list.sort(key=lambda x: x[0])
        codes = [s[1] for s in stop_list]
        times = [s[2] for s in stop_list]
        trip_info = trips[trip_id]
        rid = trip_info['route_id']
        route_trip_seqs[rid].append({
            'codes': codes,
            'times': times,
            'headsign': trip_info['headsign'],
            'service_id': trip_info['service_id'],
        })

    return route_trip_seqs

def best_sequence(trip_seqs):
    """Pick the most common stop sequence for a route"""
    from collections import Counter
    seq_counts = Counter(tuple(t['codes']) for t in trip_seqs)
    best = seq_counts.most_common(1)[0][0]
    # Find a trip with this sequence to get times
    for t in trip_seqs:
        if tuple(t['codes']) == best:
            return list(best), t['times']
    return list(best), None

def codes_to_route_db(codes, times):
    """Convert list of app codes + times to ROUTE_DB format"""
    result = []
    base = times[0] if times and times[0] is not None else 0
    for i, code in enumerate(codes):
        t = times[i] if times and i < len(times) and times[i] is not None else base + i * 3
        result.append({'code': code, 'mins': t - base})
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gtfs', default='.', help='Path to GTFS directory')
    parser.add_argument('--out', default='route_db.json', help='Output JSON file')
    args = parser.parse_args()

    print("Loading stops...")
    stops = load_stops(args.gtfs)
    print(f"  {len(stops)} stops loaded")

    print("Loading trips...")
    trips = load_rail_trips(args.gtfs)
    print(f"  {len(trips)} rail trips loaded")

    print("Building route sequences...")
    route_trip_seqs = build_route_sequences(args.gtfs, stops, trips)

    # Build ROUTE_DB
    route_db = {}
    for rid, trip_seqs in sorted(route_trip_seqs.items()):
        codes, times = best_sequence(trip_seqs)
        route_db[rid] = codes_to_route_db(codes, times)
        print(f"  {rid}: {len(codes)} stops, {len(trip_seqs)} trips")

    with open(args.out, 'w') as f:
        json.dump(route_db, f, indent=2)
    print(f"\nDone. Written to {args.out}")

if __name__ == '__main__':
    main()
