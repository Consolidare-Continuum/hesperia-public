# Deprecated tests

- `retired_test_kme_triz_integration.py.txt` — tested `core.domain.pipeline.run_document`
  computing TRIZ signals directly. That coupling was removed by design (2026-07-30): core has
  no relation to any extension/module (TRIZ, TFP, clinical, or otherwise). `.txt` extension so
  pytest doesn't collect it. Two of its four original cases were core-only or pure-TRIZ and not
  actually testing the removed coupling — reintroduce those as new tests if the coverage is
  wanted (`test_active_graph_weights`, `test_get_area_adjacency_shape`), rather than reviving
  this file as-is.
