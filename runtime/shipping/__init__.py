# HESPERIA — Shipping CLI. Single entry point; service façades only.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Shipping entry point. Exposes analyze, compare, batch-analyze. No internal API."""

from runtime.shipping.cli_main import main

__all__ = ["main"]
