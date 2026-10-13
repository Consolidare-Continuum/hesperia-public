# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Billing unit discipline (structure only, not final pricing)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

BillingUnit = Literal["PER_CORPUS", "PER_BATCH", "PER_COMPARISON", "PER_MONITORED_SERIES"]


@dataclass
class UsageEstimate:
    product_sku: str
    billing_unit: str
    estimated_units: int
    complexity_band: str


def estimate_usage_units(run_request: dict[str, Any]) -> UsageEstimate:
    sku = str(run_request.get("product_sku", "HSP-TRIZ-P1"))
    n_corpus = int(run_request.get("corpus_count", 1))
    n_doc = int(run_request.get("document_count", 0))
    n_rel = int(run_request.get("relation_count", 0))
    n_export = int(run_request.get("export_bundle_count", 1))
    n_cmp = int(run_request.get("comparison_count", 0))

    if n_cmp > 0:
        unit: BillingUnit = "PER_COMPARISON"
        est = n_cmp
        band = "high" if n_cmp > 5 else "medium"
    elif n_corpus > 1:
        unit = "PER_BATCH"
        est = n_corpus
        band = "high" if n_corpus > 10 else "medium"
    elif n_doc > 500 or n_rel > 2000:
        unit = "PER_CORPUS"
        est = max(1, n_export)
        band = "high"
    else:
        unit = "PER_CORPUS"
        est = max(1, n_export)
        band = "low"

    if run_request.get("monitored_series"):
        unit = "PER_MONITORED_SERIES"
        est = max(est, int(run_request.get("series_length", 1)))

    return UsageEstimate(
        product_sku=sku,
        billing_unit=unit,
        estimated_units=max(1, est),
        complexity_band=band,
    )
