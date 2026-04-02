#!/usr/bin/env python3
"""
inject_routes.py
Reads route_db.json produced by build_routes.py and patches
the ROUTE_DB constant inside index.html with updated data.
"""

import json, re, argparse, sys

# Maps GTFS route_id prefixes to the app's ROUTE_DB keys
ROUTE_ID_TO_KEY = {
    'RWIP': ['IPW'],
    'RPIP': ['IPW'],
    'RPSP': ['SPF'],
    'RWRP': ['KPR'],
    'RWCA': ['CBT'],
    'RWNA': ['CBT'],
    'RWBR': ['BNL'],
    'RPBR': ['BNL'],
    'RPSH': ['SHC', 'SHC_DOWN'],
    'R609': ['CBT_IPW'],
    'R610': ['CBT'],
    'R612': ['CBT'],
}

STATION_NAMES = {
    'VYS':'Varsity Lakes','ROB':'Robina','NEG':'Nerang','HLN':'Helensvale',
    'CXM':'Coomera','PMP':'Pimpama','ORM':'Ormeau','BNH':'Beenleigh',
    'HVW':'Holmview','EDL':'Edens Landing','BTI':'Bethania','LGL':'Loganlea',
    'KGT':'Kingston','WDG':'Woodridge','TPK':'Trinder Park','KRY':'Kuraby',
    'FTG':'Fruitgrove','RCN':'Runcorn','ATI':'Altandi','SNB':'Sunnybank',
    'BAN':'Banoon','CEP':'Coopers Plains','SLY':'Salisbury','RKE':'Rocklea',
    'MRK':'Moorooka','YLY':'Yeerongpilly','YRG':'Yeronga','FFI':'Fairfield',
    'DTP':'Dutton Park','BGR':'Boggo Road','BRD':'Buranda','CPO':'Coorparoo',
    'NMP':'Norman Park','MNG':'Morningside','CNH':'Cannon Hill','MRR':'Murarrie',
    'HMT':'Hemmant','LDM':'Lindum','WYH':'Wynnum North','WYN':'Wynnum',
    'WYC':'Wynnum Central','MNY':'Manly','LTA':'Lota','TNS':'Thorneside',
    'BKD':'Birkdale','WLP':'Wellington Point','ORO':'Ormiston','CVN':'Cleveland',
    'SBK':'South Bank','SBE':'South Brisbane','RST':'Roma Street','CTL':'Central',
    'FVY':'Fortitude Valley','BHI':'Bowen Hills','EGJ':'Eagle Junction',
    'ALB':'Albion','WLW':'Wooloowin','CLF':'Clayfield','HDR':'Hendra',
    'ASC':'Ascot','DBN':'Doomben','BIT':'International Airport','BDT':'Domestic Airport',
    'SHC':'Shorncliffe','SGE':'Sandgate','NBD':'North Boondall','NUD':'Nudgee',
    'BDL':'Boondall','BYO':'Banyo','BHA':'Bindha','NTG':'Northgate',
    'NDA':'Nundah','TBL':'Toombul','VGI':'Virginia','SSN':'Sunshine',
    'GEB':'Geebung','ZLL':'Zillmere','CDE':'Carseldine','BDS':'Bald Hills',
    'SPN':'Strathpine','BPR':'Bray Park','LWT':'Lawnton','PET':'Petrie',
    'KLG':'Kallangur','MRD':'Murrumba Downs','MGH':'Mango Hill',
    'MJE':'Mango Hill East','RTW':'Rothwell','KRP':'Kippa-Ring',
    'FYG':'Ferny Grove','KPR':'Keperra','GRV':'Grovely','OXP':'Oxford Park',
    'MCH':'Mitchelton','GAO':'Gaythorne','ENG':'Enoggera','ADY':'Alderley',
    'NWM':'Newmarket','WLQ':'Wilston','WND':'Windsor',
    'RSW':'Rosewood','GCH':'Grandchester','MBG':'Marburg','WLN':'Walloon',
    'TGA':'Thagoona','KRB':'Karrabin','WKK':'Wulkuraka','TST':'Thomas Street',
    'IPS':'Ipswich','EIP':'East Ipswich','BOV':'Booval','BDA':'Bundamba',
    'EBV':'Ebbw Vale','DNM':'Dinmore','RVV':'Riverview','RDK':'Redbank',
    'GDA':'Goodna','GAL':'Gailes','WAC':'Wacol','DRA':'Darra','OXL':'Oxley',
    'CND':'Corinda','CHM':'Chelmer','GVL':'Graceville','SHW':'Sherwood',
    'IRP':'Indooroopilly','TRG':'Taringa','TWG':'Toowong','ACF':'Auchenflower',
    'MLT':'Milton','SPC':'Springfield Central','SPF':'Springfield','RCL':'Richlands',
    'NAM':'Nambour','YDA':'Yandina','WOB':'Woombye','PAL':'Palmwoods',
    'EDO':'Eudlo','MOH':'Mooloolah','BRW':'Beerwah','GHM':'Glasshouse Mountains',
    'ELB':'Elimbah','BBM':'Beerburrum','LBH':'Landsborough','CBT':'Caboolture',
    'MYE':'Morayfield','BPY':'Burpengary','NRB':'Narangba','DKB':'Dakabin',
    'GYN':'Gympie North','TRA':'Traveston','PMQ':'Pomona','COZ':'Cooran',
    'COO':'Cooroy',
}

def route_to_js(key, stops):
    lines = [f'  {key}: [']
    for s in stops:
        name = STATION_NAMES.get(s['code'], s['code'])
        lines.append(f"    {{code:'{s['code']}',name:'{name}',mins:{s['mins']}}},")
    lines.append('  ],')
    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--routes', required=True)
    parser.add_argument('--html', required=True)
    args = parser.parse_args()

    with open(args.routes) as f:
        route_db = json.load(f)

    with open(args.html, encoding='utf-8') as f:
        html = f.read()

    # Build merged route_db — start with existing keys, update from GTFS
    # Find existing ROUTE_DB block
    match = re.search(r'(const ROUTE_DB = \{)(.*?)(\n\};)', html, re.DOTALL)
    if not match:
        print("ERROR: Could not find ROUTE_DB in index.html")
        sys.exit(1)

    # For each GTFS route, find its app key and update
    app_route_updates = {}
    for gtfs_id, stops in route_db.items():
        prefix = gtfs_id[:4] if len(gtfs_id) >= 4 else gtfs_id
        # Try 4-char prefix, then 3-char
        keys = ROUTE_ID_TO_KEY.get(prefix) or ROUTE_ID_TO_KEY.get(gtfs_id[:3])
        if keys:
            for key in keys:
                if key not in app_route_updates:
                    app_route_updates[key] = stops

    # Rebuild ROUTE_DB block preserving keys not in GTFS
    existing_block = match.group(2)
    # Extract existing route keys
    existing_keys = re.findall(r'^\s{2}(\w+):\s*\[', existing_block, re.MULTILINE)

    new_routes = []
    for key in existing_keys:
        if key in app_route_updates:
            new_routes.append(route_to_js(key, app_route_updates[key]))
        else:
            # Keep existing — extract original block
            pattern = rf'  {key}: \[.*?\n  \],'
            orig = re.search(pattern, existing_block, re.DOTALL)
            if orig:
                new_routes.append(orig.group(0))

    new_block = '\n' + '\n'.join(new_routes) + '\n'
    new_html = html[:match.start(2)] + new_block + html[match.end(2):]

    with open(args.html, 'w', encoding='utf-8') as f:
        f.write(new_html)

    print(f"Updated {len(app_route_updates)} routes in {args.html}")

if __name__ == '__main__':
    main()
