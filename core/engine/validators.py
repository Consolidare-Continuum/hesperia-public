"""Post-execution structural validation suite."""

from __future__ import annotations

import math
from typing import Any


def validate_final_ctx(ctx: dict[str, Any]) -> None:
    families = dict(ctx.get("families") or {})
    areas = dict(ctx.get("areas") or {})
    metrics = dict(ctx.get("metrics") or {})

    for bucket_name, bucket in (("families", families), ("areas", areas)):
        for k, v in bucket.items():
            fv = float(v)
            if math.isnan(fv) or math.isinf(fv):
                raise ValueError(f"validator_invalid_number:{bucket_name}:{k}")
            if fv < 0.0:
                raise ValueError(f"validator_negative_value:{bucket_name}:{k}")

    for k, v in metrics.items():
        if isinstance(v, (int, float)):
            fv = float(v)
            if math.isnan(fv) or math.isinf(fv):
                raise ValueError(f"validator_invalid_metric:{k}")
            if abs(fv) > 1e9:
                raise ValueError(f"validator_metric_out_of_bounds:{k}")

    f_sum = sum(float(v) for v in families.values())
    a_sum = sum(float(v) for v in areas.values())
    if families and not (0.99 <= f_sum <= 1.01):
        raise ValueError("validator_invalid_family_distribution")
    if areas and not (0.99 <= a_sum <= 1.01):
        raise ValueError("validator_invalid_area_distribution")

