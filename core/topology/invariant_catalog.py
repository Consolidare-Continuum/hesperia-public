# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.3 — canonical ontology and geometry lock.
19_SPEC Release v0.3 Structural Enforcement.
Frozen constants only. No dynamic generation. No auto-correction.
Source: 16_SPEC Structural Invariants, 18_SPEC Indexing and Coordinates,
30_FAMILIES canonical.

**Default core and default module grain = 12 areas** (``AREAS``), sealed names
GOOD…DECEIT (incl. CREATION, DECEIT). Geometry is icosahedral; vectors length 12.

Optional **ten-area module** packing (indices 0–9 only) is selected by
``core.projection.area_math_grain`` (``HESPERIA_AREA_MATH_GRAIN=10``) —
helpers in ``ten_area_module`` / grain-aware ``public_projection_layer``.
Modules may declare 10 or 12; **default is 12**.
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# Geometry constants (frozen)
# -----------------------------------------------------------------------------
AREAS = 12
FAMILIES_PER_AREA = 24
HEXES_PER_FAMILY = 250
SIDES_PER_HEX = 6

TOTAL_FAMILIES = AREAS * FAMILIES_PER_AREA  # 288
TOTAL_HEXES = TOTAL_FAMILIES * HEXES_PER_FAMILY  # 72_000
TOTAL_SIDES = TOTAL_HEXES * SIDES_PER_HEX  # 432_000
SIDES_PER_FAMILY = HEXES_PER_FAMILY * SIDES_PER_HEX  # 1_500
SIDES_PER_AREA = FAMILIES_PER_AREA * SIDES_PER_FAMILY  # 36_000

# -----------------------------------------------------------------------------
# Canonical area set (12 names; topology is icosahedral surface graph)
# Sealed order kept from 0.7.0 — index = position in CANONICAL_AREA_ORDER.
# -----------------------------------------------------------------------------
CANONICAL_AREA_ORDER: tuple[str, ...] = (
    "GOOD",
    "CARE",
    "ORDER",
    "CONTROL",
    "INDIFFERENCE",
    "HARM",
    "DESTRUCTION",
    "CHAOS",
    "FREEDOM",
    "TRUTH",
    "CREATION",
    "DECEIT",
)

CANONICAL_AREA_SET: frozenset[str] = frozenset(CANONICAL_AREA_ORDER)

# -----------------------------------------------------------------------------
# AREA_FAMILY_MAP: area name -> tuple of 24 family names (canonical order)
# Sourced from the genesis book-corpus-derived taxonomy (sphere/families.txt in
# sphereV_0.1_.zip) — see docs/foundations/genesis_taxonomy_provenance.md.
# Area order kept as sealed in 0.7.0; only family names were adopted from genesis.
# -----------------------------------------------------------------------------
AREA_FAMILY_MAP: dict[str, tuple[str, ...]] = {
    "GOOD": (
        "Altruism", "Protection", "Healing", "Mercy", "Generosity", "Mentorship",
        "Community", "Hospitality", "Forgiveness", "Integrity", "Gratitude", "Stewardship",
        "Solidarity", "Rehabilitation", "Inclusion", "Fairness", "Conservation", "Education",
        "Mediation", "Service", "Safety", "Trust", "Compassion", "Courage",
    ),
    "CARE": (
        "Compassion", "Nursing", "Comfort", "Inclusion", "Medication", "Preservation",
        "Protection", "Support", "Accessibility", "Attendance", "De-escalation", "Mediation",
        "Restore", "Shelter", "Help", "Hospitality", "Security", "Stewardship",
        "Volunteerism", "Aid", "Mentoring", "Kindness", "Responsibility", "Guardianship",
    ),
    "ORDER": (
        "Standard", "Schedule", "Governance", "Access", "Quality", "Documentation",
        "Change", "Response", "Risk", "Roles", "Versioning", "Backups",
        "Budgeting", "Compliance", "Protocol", "Checklists", "Metrics", "Playbooks",
        "Workflows", "Symmetry", "Capacity", "Directives", "Escalation", "Review",
    ),
    "CONTROL": (
        "Safeguards", "Takedowns", "Isolation", "Entitlements", "Inspection", "Permit",
        "Monitoring", "Revocation", "Gatekeeping", "Centralization", "Price-controls", "Curfews",
        "Hierarchy", "Quarantine", "Listing", "Blocklist", "Moderation", "Statutes",
        "Oversight", "Safety", "Regulation", "Supervise", "Register", "Directing",
    ),
    "INDIFFERENCE": (
        "Neglect", "Ostracism", "Dodging", "Dehumanization", "Bystanding", "Callousness",
        "Withholding", "Buckpassing", "Neutrality", "Ghosting", "Stonewalling", "Tokenism",
        "Cynicism", "Burnout", "Complacency", "Apathy", "Stalling", "Exclusion",
        "Detachment", "Ignorance", "Dumping", "Negation", "Dispassion", "Nonchalance",
    ),
    "HARM": (
        "Violence", "Exploitation", "Corruption", "Betrayal", "Negligence", "Oppression",
        "Sabotage", "Fraud", "Defamation", "Addiction-harms", "Pollution", "Waste",
        "Harassment", "Hatred", "Vengeance", "Coercion", "Intimidation", "Injury",
        "Predation", "Hazard", "Dereliction", "Cronyism", "Ruthlessness", "Vandalism",
    ),
    "DESTRUCTION": (
        "Decommissioning", "Strike", "Refusal", "Pruning", "Culling", "Removal",
        "Dismantling", "Erasure", "Neutralization", "Demolition", "Invasion", "Destroying",
        "Death", "Aggression", "Eradication", "Damage", "Shred", "Unlearning",
        "Collapse", "Devastation", "Splitting", "Partition", "Decay", "Recalls",
    ),
    "CHAOS": (
        "Swarming", "Drift", "Ideation", "Divergence", "Disruption", "Anomaly",
        "Emergence", "Volatility", "Strife", "Outliers", "Discord", "Subversion",
        "Hijacking", "Turmoil", "Commotion", "Mutation", "Instigation", "Manias",
        "Randomness", "Madness", "Instability", "Confusion", "Entropy", "Disorder",
    ),
    "FREEDOM": (
        "Autonomy", "Consent", "Openness", "Exit", "Entry", "Expression",
        "Privacy", "Mobility", "Permissionless", "Association", "Liberties", "Sandbox-testing",
        "Experimentation", "Representation", "Choice", "Interoperability", "Transparency", "Decentralization",
        "Pluralism", "Tolerance", "Whistleblowing", "Laws", "Rights", "Fair",
    ),
    "TRUTH": (
        "Evidence", "Measurement", "Reproducibility", "Transparency", "Auditability", "Citation",
        "Calibration", "Openness", "Review", "Clarity", "Fallibilism", "Verification",
        "Signal", "Validation", "Versioning", "Explainability", "Groundtruth", "Traceability",
        "Definitions", "Taxonomy", "Testing", "Methodology", "Consensus", "Uncertainty",
    ),
    "DECEIT": (
        "Lies", "Propaganda", "Falsehood", "Concealment", "Forgery", "Invalid",
        "Scapegoating", "Gaslighting", "Unbalance", "Pseudostatistics", "Plagiarism", "Clickbait",
        "Trickery", "Scams", "Mendacity", "Imposture", "Subterfuge", "Conspiracism",
        "Mislabeling", "Duplicity", "Fraudulence", "Misattribution", "Chicanery", "Hoaxes",
    ),
    "CREATION": (
        "Invention", "Design", "Craft", "Cultivation", "Engineering", "Composition",
        "Music-and-rhythm", "Writing", "Entrepreneurship", "Fusion", "Toolmaking", "Discovery",
        "Integration", "Prototyping", "Refactoring", "Synthesis", "Pattern-language", "User-experience",
        "Renovation", "Production", "Growth", "Art", "Researching", "Collaboration",
    ),
}

# Ensure exactly 12 areas and 24 families per area
assert len(CANONICAL_AREA_SET) == AREAS
assert len(CANONICAL_AREA_ORDER) == AREAS
assert set(CANONICAL_AREA_ORDER) == CANONICAL_AREA_SET
for _area, _fams in AREA_FAMILY_MAP.items():
    assert _area in CANONICAL_AREA_SET
    assert len(_fams) == FAMILIES_PER_AREA


def forward(
    area: int,
    family_local: int,
    hex_local: int,
    side_local: int,
) -> int:
    """
    Coord → sideId. 0-based.
    area in [0, AREAS), family_local in [0, FAMILIES_PER_AREA), etc.
    """
    family_global = area * FAMILIES_PER_AREA + family_local
    return ((family_global * HEXES_PER_FAMILY + hex_local) * SIDES_PER_HEX) + side_local


def inverse(side_id: int) -> tuple[int, int, int, int]:
    """
    sideId → (area, familyLocal, hexIndex, sideIndex). 0-based.
    """
    side_index = side_id % SIDES_PER_HEX
    tmp = side_id // SIDES_PER_HEX
    hex_index = tmp % HEXES_PER_FAMILY
    family_global = tmp // HEXES_PER_FAMILY
    area = family_global // FAMILIES_PER_AREA
    family_local = family_global % FAMILIES_PER_AREA
    return (area, family_local, hex_index, side_index)


def validate_coord(area: int, family_local: int, hex_local: int, side_local: int) -> None:
    """Raise if any coord out of range (HARD_STOP for family/area/hex/side overflow)."""
    if not (0 <= area < AREAS):
        raise RuntimeError(f"Sigma HARD_STOP: area must be in [0,{AREAS}), got {area}") from None
    if not (0 <= family_local < FAMILIES_PER_AREA):
        raise RuntimeError(
            f"Sigma HARD_STOP: family_local must be in [0,{FAMILIES_PER_AREA}), got {family_local}"
        ) from None
    if not (0 <= hex_local < HEXES_PER_FAMILY):
        raise RuntimeError(
            f"Sigma HARD_STOP: hex_local must be in [0,{HEXES_PER_FAMILY}), got {hex_local}"
        ) from None
    if not (0 <= side_local < SIDES_PER_HEX):
        raise RuntimeError(
            f"Sigma HARD_STOP: side_local must be in [0,{SIDES_PER_HEX}), got {side_local}"
        ) from None


def validate_side_id(side_id: int) -> None:
    """Raise if side_id not in [0, TOTAL_SIDES) (HARD_STOP for sideId overflow)."""
    if not (0 <= side_id < TOTAL_SIDES):
        raise RuntimeError(
            f"Sigma HARD_STOP: sideId must be in [0,{TOTAL_SIDES}), got {side_id}"
        ) from None
