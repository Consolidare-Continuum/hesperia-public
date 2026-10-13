# LEVEL 4 Dict-A: lexical markers → concept nodes (Dict-B). LEVEL 9: phrase marker index.
from hesperia.ontology.dictA.loader import (
    load_lexical_markers,
    build_marker_to_concepts,
    build_phrase_marker_index,
    build_colloquial_marker_index,
    load_stopwords,
    get_marker_stats,
)

__all__ = [
    "load_lexical_markers",
    "build_marker_to_concepts",
    "build_phrase_marker_index",
    "build_colloquial_marker_index",
    "load_stopwords",
    "get_marker_stats",
]
