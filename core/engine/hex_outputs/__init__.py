# HESPERIA — Hex microphysics → product analytical maps
#
# Does not re-export research.hex_outputs_e2e here (hex_microstructure_bundle_for_text /
# slim_microstructure_for_json) — core/engine must not import research.* per
# tools/check_forbidden_zone_imports.py policy, and no caller actually used this path anyway;
# real callers (runtime/pipeline/run_e2e_all.py, run_tfp_file_pipeline.py) already import
# research.hex_outputs_e2e directly.
from core.engine.hex_outputs.hex_output_engine import (
    HexOutputParams,
    attach_hex_product_outputs,
    attach_microstructure_analytics_public,
    build_sparse_hex_scene,
    compute_hex_outputs,
    serialize_hex_outputs,
)

__all__ = [
    "HexOutputParams",
    "compute_hex_outputs",
    "serialize_hex_outputs",
    "build_sparse_hex_scene",
    "attach_hex_product_outputs",
    "attach_microstructure_analytics_public",
]
