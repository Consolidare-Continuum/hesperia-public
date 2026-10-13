# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""HESPERIA core engine: orchestration backbone (module loading, execution graph, aggregation),
hex/energy field physics, matrix/PCH builders, and the DLCR lexical pipeline.

Graduated to core 2026-07-31 from hesperia/engine/ — the generic, module-agnostic runtime
machinery. TFP-specific math, calibration bundles, concept-dictionary semantics, and
clinical/TRIZ-coupled code (kme/) stayed behind in hesperia/engine/ by design; this package
must have no relation to any one module's domain semantics, same invariant as core/math and
core/topology (see docs/foundations/genesis_taxonomy_provenance.md, core/domain/pipeline.py).
"""
