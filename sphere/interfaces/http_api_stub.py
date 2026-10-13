# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
HTTP API stub — future transport layer. Do not implement yet.
Keeps transport separate from engine; endpoints defined for later implementation.
"""

# Future endpoints:
#
#   POST /analyze
#     Request body: { "text": "law regulation statute", "config": {...} }
#     Response: { "document_id": "doc_001", "usf": {...}, "diagnostics": [...] }
#
#   GET /usf/{id}
#     Returns USF artifact for document id (if stored).
#
#   POST /compare
#     Request body: { "usf_a": {...}, "usf_b": {...} }
#     Response: { "same_schema_version": bool, "metric_deltas": {...}, ... }
#
#   POST /debug
#     Request body: { "text": "...", "config": {...}, "layers": [3, 4, 5] }
#     Response: { "layer_3": {...}, "layer_4": {...}, "layer_5": {...} }
#
# Implementation: wire these to sphere.interfaces.structural_api.analyze_text,
# sphere.interfaces.usf_api.get_usf/serialize_usf/compare_usf,
# sphere.interfaces.debug_interface.debug_pipeline. Do not embed business logic in HTTP layer.
