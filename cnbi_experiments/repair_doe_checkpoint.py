"""Replace preflighted geometries and quarantine results tied to rejected anchors."""
import json
from pathlib import Path
import shutil

import pandas as pd


ROOT = Path("experimental_results")
OUTPUT = ROOT / "doe_legacy_generator"
SOURCE = ROOT / "failed_cases_original_generator"
QUARANTINE = OUTPUT / "rejected_geometry_nx3_m7_high"


def main():
    QUARANTINE.mkdir(parents=True, exist_ok=True)
    rejected = "doe_nx3_m7_high"
    for path in OUTPUT.glob(f"{rejected}*"):
        if path.is_file():
            shutil.move(str(path), str(QUARANTINE / path.name))

    shutil.copy2(SOURCE / f"{rejected}_spread_anchors.npz",
                 OUTPUT / f"{rejected}_anchors.npz")

    approved = "doe_nx5_m7_high"
    old_anchor = OUTPUT / f"{approved}_anchors.npz"
    old_reference = OUTPUT / f"{approved}_reference.npz"
    for path in (old_anchor, old_reference):
        if path.exists():
            shutil.move(str(path), str(QUARANTINE / path.name))
    shutil.copy2(SOURCE / f"{approved}_anchors.npz",
                 OUTPUT / f"{approved}_anchors.npz")

    complete_path = OUTPUT / "campaign_complete.csv"
    complete = pd.read_csv(complete_path)
    removed = int(complete.scenario_id.eq(rejected).sum())
    complete = complete[complete.scenario_id.ne(rejected)].copy()
    complete.to_csv(complete_path, index=False)

    prep_path = OUTPUT / "preparation.json"
    prep = json.loads(prep_path.read_text(encoding="utf-8"))
    spread = json.loads((SOURCE / f"{rejected}_spread_calibration.json").read_text(encoding="utf-8"))
    original = json.loads((SOURCE / "calibration.json").read_text(encoding="utf-8"))
    audits = {rejected: spread, approved: original[approved]}
    for item in prep:
        scenario_id = item["scenario_id"]
        if scenario_id in audits:
            seconds = item.get("seconds")
            item.clear()
            item.update(scenario_id=scenario_id, status="CALIBRATED", seconds=seconds,
                        **audits[scenario_id])
    prep_path.write_text(json.dumps(prep, indent=2), encoding="utf-8")
    print(json.dumps({"removed_checkpoint_rows": removed,
                      "remaining_checkpoint_rows": len(complete),
                      "replacements": list(audits)}, indent=2))


if __name__ == "__main__":
    main()
