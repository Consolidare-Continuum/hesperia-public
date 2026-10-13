"""Deterministic hex-state dynamics primitives."""

from __future__ import annotations

from core.dynamics.operator import compute_h_total
from core.state.semantic_state import SemanticState


def _as_state(state: SemanticState | dict[str, float]) -> SemanticState:
    if isinstance(state, SemanticState):
        return state
    return SemanticState(mass_vector={k: float(v) for k, v in state.items()})


def apply_decay(state: SemanticState | dict[str, float], decay: float = 0.05) -> SemanticState | dict[str, float]:
    st = _as_state(state)
    next_mass, _ = compute_h_total(
        st.mass_vector,
        {
            "decay": decay,
            "coupling_alpha": 0.0,
            "inhibition_alpha": 0.0,
        },
    )
    out = st.with_mass(next_mass)
    if isinstance(state, SemanticState):
        return out
    return out.mass_vector


def apply_decay_with_diagnostics(
    state: SemanticState | dict[str, float], decay: float = 0.05
) -> tuple[SemanticState | dict[str, float], dict[str, float | bool]]:
    st = _as_state(state)
    next_mass, diagnostics = compute_h_total(
        st.mass_vector,
        {
            "decay": decay,
            "coupling_alpha": 0.0,
            "inhibition_alpha": 0.0,
        },
    )
    out = st.with_mass(next_mass)
    if isinstance(state, SemanticState):
        return out, diagnostics
    return out.mass_vector, diagnostics


def concentration_index(state: SemanticState | dict[str, float]) -> float:
    st = _as_state(state)
    total = sum(st.mass_vector.values())
    if total <= 0:
        return 0.0
    peak = max(st.mass_vector.values())
    return peak / total


def dispersion_index(state: SemanticState | dict[str, float]) -> float:
    st = _as_state(state)
    total = sum(st.mass_vector.values())
    if total <= 0:
        return 0.0
    post, _ = compute_h_total(
        st.mass_vector,
        {
            "decay": 0.0,
            "coupling_alpha": 0.0,
            "inhibition_alpha": 0.0,
        },
    )
    active = sum(1 for value in post.values() if value > 0)
    return active / max(1, len(post))


def smooth_toward_mean(
    state: SemanticState | dict[str, float], alpha: float = 0.12
) -> SemanticState | dict[str, float]:
    """
    Deterministic denoising: blend each mass with global mean (Ethan PO-17).

    ``alpha`` in [0,1]; 0 returns input unchanged.
    """
    st = _as_state(state)
    if alpha <= 0 or not st.mass_vector:
        return state
    next_mass, _ = compute_h_total(
        st.mass_vector,
        {
            "decay": 0.0,
            "coupling_alpha": alpha,
            "inhibition_alpha": 0.0,
        },
    )
    out = st.with_mass(next_mass)
    if isinstance(state, SemanticState):
        return out
    return out.mass_vector

