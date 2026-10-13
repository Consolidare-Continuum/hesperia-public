"""Default modules: universal, domain-agnostic capabilities (dict_a, dict_b, topology, metrics)
used by every branch (TFP, MRT, COBALT, ...) — Class A in docs/specs/HESPERIA-CORE-MODULES-AND-BRANCHES.md.
Distinct from hesperia/modules/{nlp,tfp}/: those are domain-specific branches (Class B).

Corpus seal: Class A book prose lives under ``hesperia/modules/default/corpus/syzif`` only.
TFP corpora live under ``hesperia/modules/tfp/`` only — never mixed into default calibration
(see docs/specs/HESPERIA-CORE-DEFAULT-VS-TFP-CALIBRATION-SEAL.md).
"""
