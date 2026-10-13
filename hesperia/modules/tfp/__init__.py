"""TFP module package — v1 public surface.

Stable entrypoints: see ``ENTRYPOINTS.md`` in this directory.
"""

from __future__ import annotations

from hesperia.modules.tfp.field_dynamics_consumer import (
    C1_KEYS,
    C2_KEYS,
    C3_KEYS,
    C4_KEYS,
    C5_KEYS,
    TFP_FD_CONSUMER_ID,
    TFP_FD_ENV,
    build_tfp_fd_param_envelope,
    run_tfp_field_dynamics_artifact,
    run_tfp_hspr_offline_calib_job,
    tfp_field_dynamics_enabled,
)
from hesperia.modules.tfp.module import create
from hesperia.modules.tfp.v1 import TFPModule, create as create_v1

__all__ = [
    "C1_KEYS",
    "C2_KEYS",
    "C3_KEYS",
    "C4_KEYS",
    "C5_KEYS",
    "TFPModule",
    "TFP_FD_CONSUMER_ID",
    "TFP_FD_ENV",
    "build_tfp_fd_param_envelope",
    "create",
    "create_v1",
    "run_tfp_field_dynamics_artifact",
    "run_tfp_hspr_offline_calib_job",
    "tfp_field_dynamics_enabled",
]
