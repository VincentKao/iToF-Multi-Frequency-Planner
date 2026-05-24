"""Core math for iToF frequency planning.

All public functions accept modulation frequencies in MHz and return distances
in meters unless the function name says otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import gcd, pi, sqrt
from typing import Iterable

C = 299_792_458.0


@dataclass(frozen=True)
class FrequencyResult:
    frequency_mhz: float
    unambiguous_range_m: float
    precision_m: float | None


@dataclass(frozen=True)
class PairResult:
    f1_mhz: float
    f2_mhz: float
    range_1_m: float
    range_2_m: float
    synthetic_range_m: float
    precision_1_m: float | None
    precision_2_m: float | None
    combined_precision_m: float | None
    beat_noise_m: float | None
    noise_amplification_factor: float
    robustness: str


@dataclass(frozen=True)
class MultiFrequencyResult:
    frequencies_mhz: tuple[float, ...]
    single_ranges_m: tuple[float, ...]
    synthetic_range_m: float
    pair_ranges_m: tuple[tuple[float, float, float], ...]
    combined_precision_m: float | None
    min_pair_delta_mhz: float
    beat_noise_m: float | None
    noise_amplification_factor: float
    robustness: str


@dataclass(frozen=True)
class CandidateResult:
    frequencies_mhz: tuple[float, ...]
    synthetic_range_m: float
    combined_precision_m: float
    beat_noise_m: float
    min_pair_delta_mhz: float
    score: float
    meets_range: bool
    meets_precision: bool


def mhz_to_hz(frequency_mhz: float) -> float:
    _validate_frequency(frequency_mhz)
    return frequency_mhz * 1_000_000.0


def unambiguous_range_m(frequency_mhz: float) -> float:
    """Single-frequency unambiguous range: R = c / (2f)."""
    return C / (2.0 * mhz_to_hz(frequency_mhz))


def distance_precision_m(frequency_mhz: float, phase_noise_rad: float) -> float:
    """Distance standard deviation from phase noise.

    sigma_d = c / (4*pi*f) * sigma_phi
    """
    _validate_phase_noise(phase_noise_rad)
    return C / (4.0 * pi * mhz_to_hz(frequency_mhz)) * phase_noise_rad


def synthetic_range_m(f1_mhz: float, f2_mhz: float) -> float:
    """Two-frequency synthetic range: c / (2*|f1-f2|)."""
    _validate_distinct_pair(f1_mhz, f2_mhz)
    delta_hz = abs(f1_mhz - f2_mhz) * 1_000_000.0
    return C / (2.0 * delta_hz)


def analyze_frequency(
    frequency_mhz: float, phase_noise_rad: float | None = None
) -> FrequencyResult:
    precision = (
        distance_precision_m(frequency_mhz, phase_noise_rad)
        if phase_noise_rad is not None
        else None
    )
    return FrequencyResult(
        frequency_mhz=frequency_mhz,
        unambiguous_range_m=unambiguous_range_m(frequency_mhz),
        precision_m=precision,
    )


def analyze_pair(
    f1_mhz: float, f2_mhz: float, phase_noise_rad: float | None = None
) -> PairResult:
    _validate_distinct_pair(f1_mhz, f2_mhz)
    precision_1 = (
        distance_precision_m(f1_mhz, phase_noise_rad)
        if phase_noise_rad is not None
        else None
    )
    precision_2 = (
        distance_precision_m(f2_mhz, phase_noise_rad)
        if phase_noise_rad is not None
        else None
    )
    combined = _combined_precision((f1_mhz, f2_mhz), phase_noise_rad)
    beat_noise = _beat_noise_m(abs(f1_mhz - f2_mhz), phase_noise_rad)
    noise_amp = _noise_amplification_factor((f1_mhz, f2_mhz))
    return PairResult(
        f1_mhz=f1_mhz,
        f2_mhz=f2_mhz,
        range_1_m=unambiguous_range_m(f1_mhz),
        range_2_m=unambiguous_range_m(f2_mhz),
        synthetic_range_m=synthetic_range_m(f1_mhz, f2_mhz),
        precision_1_m=precision_1,
        precision_2_m=precision_2,
        combined_precision_m=combined,
        beat_noise_m=beat_noise,
        noise_amplification_factor=noise_amp,
        robustness=_classify_robustness(noise_amp, beat_noise),
    )


def analyze_multi_frequency(
    frequencies_mhz: Iterable[float], phase_noise_rad: float | None = None
) -> MultiFrequencyResult:
    frequencies = tuple(float(f) for f in frequencies_mhz)
    _validate_frequency_set(frequencies)

    pair_ranges = tuple(
        (a, b, synthetic_range_m(a, b)) for a, b in combinations(frequencies, 2)
    )
    deltas = tuple(abs(a - b) for a, b in combinations(frequencies, 2))
    min_delta = min(deltas)
    noise_amp = _noise_amplification_factor(frequencies)
    beat_noise = _beat_noise_m(min_delta, phase_noise_rad)

    return MultiFrequencyResult(
        frequencies_mhz=frequencies,
        single_ranges_m=tuple(unambiguous_range_m(f) for f in frequencies),
        synthetic_range_m=_multi_frequency_repeat_range_m(frequencies),
        pair_ranges_m=pair_ranges,
        combined_precision_m=_combined_precision(frequencies, phase_noise_rad),
        min_pair_delta_mhz=min_delta,
        beat_noise_m=beat_noise,
        noise_amplification_factor=noise_amp,
        robustness=_classify_robustness(noise_amp, beat_noise),
    )


def search_frequency_sets(
    min_frequency_mhz: float,
    max_frequency_mhz: float,
    step_mhz: float,
    count: int,
    max_distance_m: float,
    target_precision_m: float,
    phase_noise_rad: float,
    limit: int = 10,
) -> list[CandidateResult]:
    """Search frequency combinations and rank them by range/precision trade-off."""
    _validate_frequency(min_frequency_mhz)
    _validate_frequency(max_frequency_mhz)
    _validate_frequency(step_mhz)
    if min_frequency_mhz >= max_frequency_mhz:
        raise ValueError("min_frequency_mhz must be smaller than max_frequency_mhz")
    if count < 2:
        raise ValueError("count must be at least 2")
    if max_distance_m <= 0:
        raise ValueError("max_distance_m must be positive")
    if target_precision_m <= 0:
        raise ValueError("target_precision_m must be positive")
    _validate_phase_noise(phase_noise_rad)

    grid = _frequency_grid(min_frequency_mhz, max_frequency_mhz, step_mhz)
    results: list[CandidateResult] = []
    for combo in combinations(grid, count):
        analysis = analyze_multi_frequency(combo, phase_noise_rad)
        precision = analysis.combined_precision_m
        beat_noise = analysis.beat_noise_m
        if precision is None or beat_noise is None:
            continue
        meets_range = analysis.synthetic_range_m >= max_distance_m
        meets_precision = precision <= target_precision_m
        score = _score_candidate(
            synthetic_range_m=analysis.synthetic_range_m,
            precision_m=precision,
            beat_noise_m=beat_noise,
            required_range_m=max_distance_m,
            target_precision_m=target_precision_m,
        )
        results.append(
            CandidateResult(
                frequencies_mhz=combo,
                synthetic_range_m=analysis.synthetic_range_m,
                combined_precision_m=precision,
                beat_noise_m=beat_noise,
                min_pair_delta_mhz=analysis.min_pair_delta_mhz,
                score=score,
                meets_range=meets_range,
                meets_precision=meets_precision,
            )
        )

    results.sort(
        key=lambda item: (
            item.meets_range,
            item.meets_precision,
            item.score,
            -item.beat_noise_m,
        ),
        reverse=True,
    )
    return results[:limit]


def _combined_precision(
    frequencies_mhz: tuple[float, ...], phase_noise_rad: float | None
) -> float | None:
    if phase_noise_rad is None:
        return None
    variances = [
        distance_precision_m(frequency_mhz, phase_noise_rad) ** 2
        for frequency_mhz in frequencies_mhz
    ]
    return 1.0 / sqrt(sum(1.0 / variance for variance in variances))


def _beat_noise_m(delta_mhz: float, phase_noise_rad: float | None) -> float | None:
    if phase_noise_rad is None:
        return None
    _validate_frequency(delta_mhz)
    return C / (4.0 * pi * delta_mhz * 1_000_000.0) * sqrt(2.0) * phase_noise_rad


def _noise_amplification_factor(frequencies_mhz: tuple[float, ...]) -> float:
    max_frequency = max(frequencies_mhz)
    min_delta = min(abs(a - b) for a, b in combinations(frequencies_mhz, 2))
    return max_frequency / min_delta


def _multi_frequency_repeat_range_m(frequencies_mhz: tuple[float, ...]) -> float:
    # If frequencies are placed on an integer-Hz grid, the joint phase pattern
    # repeats every c / (2*gcd(f_i)).
    frequencies_hz = [round(f * 1_000_000) for f in frequencies_mhz]
    common = frequencies_hz[0]
    for frequency_hz in frequencies_hz[1:]:
        common = gcd(common, frequency_hz)
    return C / (2.0 * common)


def _frequency_grid(
    min_frequency_mhz: float, max_frequency_mhz: float, step_mhz: float
) -> tuple[float, ...]:
    values: list[float] = []
    current = min_frequency_mhz
    epsilon = step_mhz / 1_000_000.0
    while current <= max_frequency_mhz + epsilon:
        values.append(round(current, 9))
        current += step_mhz
    return tuple(values)


def _score_candidate(
    synthetic_range_m: float,
    precision_m: float,
    beat_noise_m: float,
    required_range_m: float,
    target_precision_m: float,
) -> float:
    range_term = min(synthetic_range_m / required_range_m, 1.0)
    precision_term = min(target_precision_m / precision_m, 1.0)
    robustness_term = 1.0 / (1.0 + beat_noise_m / target_precision_m)
    return 100.0 * (0.45 * range_term + 0.35 * precision_term + 0.20 * robustness_term)


def _classify_robustness(
    noise_amplification_factor: float, beat_noise_m: float | None
) -> str:
    if beat_noise_m is not None:
        if beat_noise_m < 0.005:
            return "High"
        if beat_noise_m < 0.02:
            return "Medium"
        return "Low"
    if noise_amplification_factor < 8.0:
        return "High"
    if noise_amplification_factor < 20.0:
        return "Medium"
    return "Low"


def _validate_frequency(frequency_mhz: float) -> None:
    if frequency_mhz <= 0:
        raise ValueError("frequency must be positive")


def _validate_phase_noise(phase_noise_rad: float) -> None:
    if phase_noise_rad < 0:
        raise ValueError("phase_noise_rad must be non-negative")


def _validate_distinct_pair(f1_mhz: float, f2_mhz: float) -> None:
    _validate_frequency(f1_mhz)
    _validate_frequency(f2_mhz)
    if f1_mhz == f2_mhz:
        raise ValueError("frequencies must be distinct")


def _validate_frequency_set(frequencies_mhz: tuple[float, ...]) -> None:
    if len(frequencies_mhz) < 2:
        raise ValueError("at least two frequencies are required")
    for frequency_mhz in frequencies_mhz:
        _validate_frequency(frequency_mhz)
    if len(set(frequencies_mhz)) != len(frequencies_mhz):
        raise ValueError("frequencies must be distinct")
