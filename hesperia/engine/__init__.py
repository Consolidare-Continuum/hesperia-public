# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""HESPERIA engine: module-specific semantics — concept dictionaries, TFP math/calibration,
KME (Knowledge Metrics Engine, clinical/TRIZ-coupled), hesperia_control readout policy.

Generic orchestration/physics/matrix code graduated to core.engine 2026-07-31 — this package
now holds only what's tied to a specific module's domain semantics (dicts, corpus-derived
calibration bundles, TFP-tuned thresholds), not universal engine plumbing.
"""
