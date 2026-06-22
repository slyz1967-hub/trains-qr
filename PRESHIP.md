# TRAINS — Pre-Ship Checklist

Run every step on a real phone before a build goes live. Ship only if all pass.

## 1. Self-check (Dev Mode)
- [ ] Dev Mode → Self-check: every row green.

## 2. Run report survives relaunch (Altered)
- [ ] Build an Altered/Route Builder sheet.
- [ ] Enter 3+ departure times, a Driver name, and Unit numbers.
- [ ] Force-close the app (or wait out the timeout).
- [ ] Reopen → all times, driver, units still there, unchanged.

## 3. Run report survives relaunch (rostered)
- [ ] Open a rostered job-card run sheet, enter 2+ times.
- [ ] Force-close, reopen → times intact.

## 4. Diary — two shift notes, same day/card
- [ ] Sign off with a shift note.
- [ ] Sign back in (same job card), add a second note.
- [ ] Sign off → diary entry shows BOTH notes, neither lost.

## 5. Late running
- [ ] Enter an on-time run (0 min) and a late run.
- [ ] Supervisor Dashboard / Diary / stat tiles: only the late one appears in Late Running.

## 6. Beenleigh timing spot-check
- [ ] Build DG40 / DM29 (Bowen Hills ↔ Beenleigh).
- [ ] Suburban stops sit on the booked times (no creeping +1/+8).

## 7. Version
- [ ] Update banner shows the new version and installs cleanly (no reinstall loop).

---
If any step fails: do not ship. Fix, re-bump, re-run from step 1.
