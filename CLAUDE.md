# TRAINS — Queensland Rail guard run-sheet app

A single-file PWA for QR guards: roster, job cards, run sheets, run reports, diary,
crew handover and a developer panel. Everything lives in one `index.html`
(~110k lines, ~3 MB): all HTML, CSS (`<style>` blocks) and JS (`<script>` blocks)
are inline. There is **no build step and no dependencies** — edit `index.html`
and push to GitHub Pages.

- Live: https://slyz1967-hub.github.io/trains-qr/index.html
- It is a PWA (installs to the home screen); on load it unregisters service
  workers and runs with no-cache headers, so a version bump is how updates reach guards.

## Releasing a change — do ALL of these together, every time

1. **Bump the version in THREE places** (use any number higher than the current one):
   - the `<!--TRAINS_VERSION:NNNN-->` comment at the very top of the file (line ~3)
   - the in-DOM `TRAINS_VERSION` marker just after `<body>`
   - the `CURRENT_VERSION` JS const (~line 200)
   `CURRENT_VERSION` drives the on-load update banner; the `TRAINS_VERSION` comment is
   fetched from the server by `checkVersionFromServer()` to detect updates in PWA mode.
   If these drift apart, the update banner and Self-check break.
2. **Add a changelog entry** to `TRAINS_CHANGELOG` (~line 95416). The key must match
   `CURRENT_VERSION` exactly — guards read it in "What's New?" on update.
3. **Add a `<!--TRAINS_UPDATE:NNNN - description-->` comment** near the top of the file
   describing what changed.
4. **Run the Self-check** (Developer Panel → 🛡 Self-check) on-device after the change.
   It asserts version sync, that a changelog entry exists, GTFS is loaded, station codes
   are applied, and the key run-report/diary guards are present. A red row is a regression.

## Sensitive subsystems — change surgically and say what you touched

These are the parts that have regressed repeatedly. Every `TRAINS_UPDATE` comment ends by
stating which of these it did **not** touch — keep that discipline:

> *timetable (GTFS) data · route arrays · sectional running times · station names · diary · rostered cards · version logic*

## Station codes — two schemes, bridged (do NOT blanket-rename)

Job cards/rosters use **official QR codes**; the bundled GTFS feed and route arrays use a
**different scheme**. They are reconciled, not unified:

- `CANONICAL_STATION_NAMES` is the source of truth for corrected names; a self-healing
  routine re-applies it onto `STATION_NAMES` on every load. This lives in a marked
  **DO NOT REMOVE** block — `STATION_NAMES` gets regenerated and silently loses manual fixes.
- `ROSTER_TO_FEED` maps official → feed codes (used at every endpoint match).
- `GTFS_CODE_MAP` maps feed → route codes (e.g. `LWT`→`LTA` for Lawnton).
- **Several codes are overloaded — never do a blanket rename:** `LTA` = Lota *and* Lawnton;
  Kippa-Ring is `KPR` (official) / `KRP` (route); Wooloowin is `WOL` (not `WLN`, which is Walloon).
  Disambiguate per array, never globally.

## Sectional running times

The interval between two adjacent stations is **fixed**, regardless of train number or
destination. Intermediate stop time = `previous_station_time + fixed_section_minutes`
(cumulative from the first stop), **not** position-based spacing.

The Gold Coast / Beenleigh / Airport corridor is special: the public GTFS feed runs 1–2 min
off the internal Working Timetable (WTT), so a shared re-time step (`_rbApplyGcWtt`) overwrites
every stop on that corridor from the authoritative WTT route arrays (`RB_GC_MINS`,
`GC_AIRPORT`/`GC_GOLD`, direction via `findRoute`), anchored to the entered first-stop time.
Other corridors keep the real GTFS sectionals — guard the re-time by corridor.

**A section time is stored in MANY parallel copies — fix every copy or it regresses.** The same
physical section appears in: the forward route array, the reverse route array, both directions of
`SECTIONAL_TIMES`, any cross-corridor array that traverses it (`BNL_FGV`/`FGV_BNL`, etc.), and the
Gold Coast trackwork templates (`VYS_BAN`/`BAN_VYS`, `VYS_BNH`/`BNH_VYS`). A "fix" that touches only
one copy gets silently undone when another path is used. When correcting any sectional, audit ALL
copies in one pass (grep both adjacent station codes) and make them agree, then verify each edited
array is strictly ascending.

**Beenleigh southern corridor — the authoritative reference, do not let it drift back.**
`BNL_FGV` (up, BNH→…) and `FGV_BNL` (down, …→BNH) are the verified arrays; every other Beenleigh
corridor array should match their offsets for the shared stops. When any Beenleigh time looks wrong,
align the whole stretch to these rather than nudging one section (the arrays carry compensating
errors that can net out at some stations, so single-section edits mislead).

Canonical cumulative offsets from Beenleigh (BNH=0):
- **Up (`BNL_FGV`):** HVW 2, EDL 5, BTI 7, LGL 11, KGT 14, WDG 18, TPK 20, KRY 24, FTG 26, RCN 28,
  ATI 30, SNB 32, BAN 34, CEP 37, SLY 40, RKE 42, MRK 44, YLY 46, YRG 48, FFI 50, DTP 52.
- **Down (`FGV_BNL`, magnitudes back to BNH):** HVW 3, EDL 6, BTI 8, LGL 12, KGT 14, WDG 18, TPK 20,
  KRY 25, FTG 27, RCN 29, ATI 31, SNB 33, BAN 35, CEP 37, SLY 40, RKE 42, MRK 45, YLY 46, YRG 48,
  FFI 50, DTP 52.

Things that keep biting: Edens Landing↔Bethania = **2** (not 3); Kuraby↔Fruitgrove = **2** (was once
coded 8); Sunnybank↔Altandi = **2** (down was 3). BNH↔HVW is **asymmetric** — 2 up, 3 down — so use the
matching array per direction, don't symmetrise. Yeerongpilly↔Moorooka = 1 and Coopers Plains↔Banoon = 2
are correct WTT values, not errors — leave them.

Arrays kept in sync with the above: `BNH_BHI` (up, the one used by both the normal builder AND the
`_rbApplyGcWtt` re-time — Beenleigh is in the GC anchor set, and `_rbApplyGcWtt` re-times from
`findRoute(BNH,BHI)` which returns `BNH_BHI`, so fixing it fixes both paths), `BHI_BNH` (down),
`SECTIONAL_TIMES` (both directions), and the trackwork templates `VYS_BAN`/`BAN_VYS` (anchor at the
Beenleigh-junction stop, rebuild the suburban offsets from the arrays above, preserve the Gold Coast
leg sections). The `BNL` fallback array carries its own unrelated drift and is not in the BNH↔BHI path.

## Run building — order of precedence

`findRoute` is the primary route builder; the actual GTFS trip is the fallback when it can't
stitch a corridor; genuine no-data legs stay anchor-only. Manual searches show the full
timetable run; the job-card segment is used only when a train is opened from its job-card
button. Watch for **corridor collisions** (a train number the feed reuses on another line) —
validate that a feed trip actually serves the rostered origin before using it.

## Data & persistence

All client-side `localStorage`, two namespaces:
- `qr-*` — app data: `qr-diary`, `qr-rs-full` (run-sheet snapshot), `qr-jc` (job cards),
  `qr-tc` (temp cards), `qr-shared-rs-*`, `qr-pending-handover`, etc.
- `trains-*` — version/session: `trains-version`, `trains-session`, `trains-update-available`.

Diary entries merge multiple sign-on/sign-off sessions into one entry **scoped by card**
(same guard + same job card + same date); reports dedupe by `id`. Don't loosen that scoping.

## Quick map of mid-file landmarks

- `CURRENT_VERSION` const ~200 · `TRAINS_CHANGELOG` ~95416 · `checkVersionFromServer()` ~95386
- Self-check assertions ~9888 / tab markup ~109724
- GTFS timetable blobs, route arrays and the canonical station-name block are mid-file —
  search by the identifier, not by line number.
