# HESPERIA — Dialogue Structure Model (TFP)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Turn, Response, InteractionPair — базовая единица TFP анализа:
Patient turn → Therapist intervention → Patient reaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hesperia.nlp.session_structure import Utterance


@dataclass
class Turn:
    """Одна реплика в диалоге (ссылка на Utterance + индекс)."""
    utterance: "Utterance"
    index: int


@dataclass
class Response:
    """Ответная реплика (следующий turn другого спикера)."""
    turn: Turn
    reply_to_index: int  # индекс реплики, на которую отвечают


@dataclass
class InteractionPair:
    """
    Базовая единица TFP: пациент → интервенция терапевта → реакция пациента.
    patient_turn → therapist_intervention → patient_reaction
    """
    patient_turn: Turn
    therapist_intervention: Turn
    patient_reaction: Turn


def build_turns(utterances: list[Any]) -> list[Turn]:
    """Преобразовать список Utterance в список Turn (с индексами)."""
    from hesperia.nlp.session_structure import Utterance

    return [Turn(utterance=u, index=i) for i, u in enumerate(utterances) if isinstance(u, Utterance)]


def build_interaction_pairs(utterances: list[Any]) -> list[InteractionPair]:
    """
    Найти все тройки P → T → P в последовательности реплик.
    Возвращает список InteractionPair (patient turn, therapist intervention, patient reaction).
    """
    from hesperia.nlp.session_structure import Utterance

    if not utterances or len(utterances) < 3:
        return []
    turns = build_turns(utterances)
    pairs: list[InteractionPair] = []
    for i in range(len(turns) - 2):
        p1, t1, p2 = turns[i], turns[i + 1], turns[i + 2]
        u1, u2, u3 = p1.utterance, t1.utterance, p2.utterance
        if u1.speaker == "patient" and u2.speaker == "therapist" and u3.speaker == "patient":
            pairs.append(InteractionPair(patient_turn=p1, therapist_intervention=t1, patient_reaction=p2))
    return pairs


def get_response_chain(turns: list[Turn], from_index: int) -> list[Response]:
    """Для реплики с индексом from_index вернуть цепочку ответов (Response)."""
    out: list[Response] = []
    i = from_index
    while i + 1 < len(turns):
        out.append(Response(turn=turns[i + 1], reply_to_index=i))
        i += 1
        if i >= len(turns):
            break
    return out
