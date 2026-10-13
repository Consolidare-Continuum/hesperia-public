"""Strict semantic state container for core execution flow."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SemanticState:
    energy_vector: dict[str, float] = field(default_factory=dict)
    activation_vector: dict[str, float] = field(default_factory=dict)
    mass_vector: dict[str, float] = field(default_factory=dict)
    position: dict[str, str] = field(default_factory=dict)

    def with_activation(self, activation_vector: dict[str, float]) -> "SemanticState":
        return SemanticState(
            energy_vector=dict(self.energy_vector),
            activation_vector=dict(activation_vector),
            mass_vector=dict(self.mass_vector),
            position=dict(self.position),
        )

    def with_mass(self, mass_vector: dict[str, float]) -> "SemanticState":
        return SemanticState(
            energy_vector=dict(self.energy_vector),
            activation_vector=dict(self.activation_vector),
            mass_vector=dict(mass_vector),
            position=dict(self.position),
        )

