#!/usr/bin/env python3
"""Checks of the weighted use case data (model 2, app/engine_app/e2e_usecases_w.py) of one page, Turkish.
Temporary copy of the skill's check_usecases.py for the new model; it moves into the skill after the owner accepts the pilot.

Usage: check_usecases_w.py APP_DIR PAGE_ID

Checks: 10 cards; 3 candidates and the page's service among them; the best fit first; 3-5 R1 sub-items from the catalog,
then R2-R5; weights sum to 100, R2-R5 at least 5, every weight has a reason; R1 is the heaviest group (or the weight note
says why not); every cell has a reason; every reason below 10 says "N puan kırıldı" with N = 10 - points; the page's
service names a feature (Ö1..Ö9) in each card; a head-to-head text of at least 95 words for every candidate after the best
fit; the verdict names the best fit first; 5 cards have a simulation and its last step gives the card's totals;
no forbidden ad-hoc term. Exit 1 when a check fails."""
import re, sys
from pathlib import Path

FORBIDDEN = [r"\btam key\b", r"\bpartition parçası\b", r"\bsıralama parçası\b", r"\bzorunlu gereksinim\b", r"\bdiskalifiye\b"]


def main(app_dir, eid):
    sys.path.insert(0, str(Path(app_dir).resolve()))
    from engine_app import e2e_sims as m, e2e_usecases_w as w
    bad = []
    data = w.USECASES_W[eid]
    page = w.PAGE_SVC[eid]
    cards = m.usecases(eid, "tr")
    sims = m.SIMS[eid]("tr")
    if len(data) != 10:
        bad.append(f"{len(data)} cards, 10 are necessary")
    if sum(1 for uc in data if uc["sim"]) != 5:
        bad.append("5 cards must have a simulation")
    for uc, card in zip(data, cards):
        name = f"card {uc['no']} {uc['id']}"
        if page not in uc["cands"]:
            bad.append(f"{name}: the page's service {page} is not a candidate")
        r1 = [r for r in uc["rows"] if r["code"] in w.R1_CATALOG]
        r1w = sum(r["w"] for r in r1)
        if any(r["w"] > r1w for r in uc["rows"][len(r1):]) or (r1w < max(r["w"] for r in uc["rows"][len(r1):]) and "R1" not in uc["wnote"][1]):
            bad.append(f"{name}: R1 ({r1w}) is not the heaviest group and the weight note does not say why")
        for r in uc["rows"]:
            if not r["wwhy"][1].strip():
                bad.append(f"{name}: {r['label']} has no weight reason")
        text = " ".join([uc["story"][1], uc["wnote"][1], uc["verdict"][1]] + [r["want"][1] + " " + r["why"][1] + " " + r["wwhy"][1] for r in uc["rows"]]
                        + [x[1][1] for c in uc["cands"] for x in uc["scores"][c]] + [t[1] for t in uc["h2h"].values()])
        for pat in FORBIDDEN:
            if re.search(pat, text, re.I):
                bad.append(f"{name}: forbidden term {pat}")
        for c in uc["cands"]:
            for r, (p, why) in zip(uc["rows"], uc["scores"][c]):
                why = why[1]
                if not why.strip():
                    bad.append(f"{name}: {c} {r['label']} has no reason")
                mm = re.search(r"(\d+) puan kırıldı", why)
                if p < 10 and (not mm or int(mm.group(1)) != 10 - p):
                    bad.append(f"{name}: {c} {r['label']} = {p} but the reason does not say '{10 - p} puan kırıldı'")
                if p == 10 and mm:
                    bad.append(f"{name}: {c} {r['label']} = 10 but the reason says points were taken off")
        if not re.search(r"\bÖ\d\b", " ".join(x[1][1] for x in uc["scores"][page])):
            bad.append(f"{name}: the reasons of {page} name no feature (Ö1..Ö9)")
        for c in uc["cands"][1:]:
            if len(uc["h2h"][c][1].split()) < 95:
                bad.append(f"{name}: head-to-head text for {c} has {len(uc['h2h'][c][1].split())} words, at least 95")
        best = m.SVC[uc["cands"][0]].split(" (")[0].split(" ")[0]
        if not uc["verdict"][1].startswith(f"Karar: {best} "):
            bad.append(f"{name}: the verdict does not name the best fit ({best}) first")
        if card["best"]["key"] != uc["cands"][0]:
            bad.append(f"{name}: the rendered card does not put the best fit first")
        if uc["sim"]:
            if uc["sim"] not in sims:
                bad.append(f"{name}: simulation {uc['sim']} is not in SIMS")
            else:
                last = sims[uc["sim"]]["steps"][-1]["out"]
                got = {row[0]: row[1] for row in last}
                for c in uc["cands"]:
                    if got.get(m.SVC[c]) != w.fmt(uc["total"][c]):
                        bad.append(f"{name}: simulation total of {c} is {got.get(m.SVC[c])}, the card says {w.fmt(uc['total'][c])}")
    print("\n".join(bad) or "usecases (weighted): OK")
    print(f"cards: {len(data)}, simulations: {sum(1 for uc in data if uc['sim'])}, best fit: "
          + ", ".join(f"{uc['no']}:{uc['cands'][0]}" for uc in data))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
