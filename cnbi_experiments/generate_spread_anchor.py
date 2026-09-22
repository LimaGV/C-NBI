"""Generate the broadest valid geometry among legacy calibration starts."""
import json
from pathlib import Path

import numpy as np

from .doe import calibrate


output = Path("experimental_results/failed_cases_original_generator")
anchors, audit = calibrate(3, 7, "high", 38085, starts=48, prefer_spread=True)
np.savez_compressed(output / "doe_nx3_m7_high_spread_anchors.npz", anchors=anchors)
(output / "doe_nx3_m7_high_spread_calibration.json").write_text(
    json.dumps(audit, indent=2), encoding="utf-8")
print(audit["achieved"], audit["attempts"][-1]["attempt"], flush=True)
