"""iToF multi-frequency planning toolkit."""

from .core import (
    C,
    CandidateResult,
    FrequencyResult,
    MultiFrequencyResult,
    PairResult,
    analyze_frequency,
    analyze_multi_frequency,
    analyze_pair,
    distance_precision_m,
    search_frequency_sets,
    synthetic_range_m,
    unambiguous_range_m,
)

__all__ = [
    "C",
    "CandidateResult",
    "FrequencyResult",
    "MultiFrequencyResult",
    "PairResult",
    "analyze_frequency",
    "analyze_multi_frequency",
    "analyze_pair",
    "distance_precision_m",
    "search_frequency_sets",
    "synthetic_range_m",
    "unambiguous_range_m",
]
