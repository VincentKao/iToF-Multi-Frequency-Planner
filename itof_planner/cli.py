"""Command line interface for the iToF planner."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .core import (
    analyze_frequency,
    analyze_multi_frequency,
    analyze_pair,
    search_frequency_sets,
)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="itof-planner",
        description="iToF multi-frequency planning and phase-unwrapping analysis tool.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("single", help="Analyze one modulation frequency.")
    single.add_argument("frequency_mhz", type=float)
    single.add_argument("--phase-noise", type=float, default=None, help="Phase noise in rad.")
    single.set_defaults(func=_single)

    pair = subparsers.add_parser("pair", help="Analyze a frequency pair.")
    pair.add_argument("f1_mhz", type=float)
    pair.add_argument("f2_mhz", type=float)
    pair.add_argument("--phase-noise", type=float, default=None, help="Phase noise in rad.")
    pair.set_defaults(func=_pair)

    multi = subparsers.add_parser("multi", help="Analyze a multi-frequency set.")
    multi.add_argument("frequencies_mhz", type=float, nargs="+")
    multi.add_argument("--phase-noise", type=float, default=None, help="Phase noise in rad.")
    multi.set_defaults(func=_multi)

    search = subparsers.add_parser("search", help="Search ranked frequency sets.")
    _add_search_args(search)
    search.add_argument("--top", type=int, default=10)
    search.set_defaults(func=_search)

    heatmap = subparsers.add_parser("heatmap", help="Export all pair metrics as CSV.")
    heatmap.add_argument("--min", type=float, required=True, dest="min_frequency_mhz")
    heatmap.add_argument("--max", type=float, required=True, dest="max_frequency_mhz")
    heatmap.add_argument("--step", type=float, required=True, dest="step_mhz")
    heatmap.add_argument("--phase-noise", type=float, default=None)
    heatmap.add_argument("--output", type=Path, required=True)
    heatmap.set_defaults(func=_heatmap)

    return parser


def _add_search_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--min", type=float, required=True, dest="min_frequency_mhz")
    parser.add_argument("--max", type=float, required=True, dest="max_frequency_mhz")
    parser.add_argument("--step", type=float, required=True, dest="step_mhz")
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--max-distance", type=float, required=True, dest="max_distance_m")
    parser.add_argument(
        "--target-precision-mm", type=float, required=True, dest="target_precision_mm"
    )
    parser.add_argument("--phase-noise", type=float, required=True, dest="phase_noise_rad")


def _single(args: argparse.Namespace) -> None:
    result = analyze_frequency(args.frequency_mhz, args.phase_noise)
    print(f"Frequency: {result.frequency_mhz:g} MHz")
    print(f"Unambiguous range: {_m(result.unambiguous_range_m)}")
    if result.precision_m is not None:
        print(f"Distance precision: {_mm(result.precision_m)}")


def _pair(args: argparse.Namespace) -> None:
    result = analyze_pair(args.f1_mhz, args.f2_mhz, args.phase_noise)
    print(f"Frequencies: {result.f1_mhz:g} MHz / {result.f2_mhz:g} MHz")
    print(f"Single range f1: {_m(result.range_1_m)}")
    print(f"Single range f2: {_m(result.range_2_m)}")
    print(f"Synthetic range: {_m(result.synthetic_range_m)}")
    print(f"Noise amplification factor: {result.noise_amplification_factor:.3g}x")
    print(f"Unwrap robustness: {result.robustness}")
    if result.precision_1_m is not None and result.precision_2_m is not None:
        print(f"Precision f1: {_mm(result.precision_1_m)}")
        print(f"Precision f2: {_mm(result.precision_2_m)}")
        print(f"Combined precision: {_mm(result.combined_precision_m)}")
        print(f"Beat noise: {_mm(result.beat_noise_m)}")


def _multi(args: argparse.Namespace) -> None:
    result = analyze_multi_frequency(args.frequencies_mhz, args.phase_noise)
    freqs = ", ".join(f"{frequency:g}" for frequency in result.frequencies_mhz)
    print(f"Frequencies: {freqs} MHz")
    print(f"Joint synthetic range: {_m(result.synthetic_range_m)}")
    print(f"Minimum pair delta: {result.min_pair_delta_mhz:g} MHz")
    print(f"Noise amplification factor: {result.noise_amplification_factor:.3g}x")
    print(f"Unwrap robustness: {result.robustness}")
    print("Single-frequency ranges:")
    for frequency, range_m in zip(result.frequencies_mhz, result.single_ranges_m):
        print(f"  {frequency:g} MHz: {_m(range_m)}")
    print("Pair synthetic ranges:")
    for f1, f2, range_m in result.pair_ranges_m:
        print(f"  {f1:g}/{f2:g} MHz: {_m(range_m)}")
    if result.combined_precision_m is not None:
        print(f"Combined precision: {_mm(result.combined_precision_m)}")
        print(f"Beat noise: {_mm(result.beat_noise_m)}")


def _search(args: argparse.Namespace) -> None:
    results = search_frequency_sets(
        min_frequency_mhz=args.min_frequency_mhz,
        max_frequency_mhz=args.max_frequency_mhz,
        step_mhz=args.step_mhz,
        count=args.count,
        max_distance_m=args.max_distance_m,
        target_precision_m=args.target_precision_mm / 1000.0,
        phase_noise_rad=args.phase_noise_rad,
        limit=args.top,
    )
    print(
        "rank | frequencies MHz | score | range | precision | beat noise | min delta | pass"
    )
    for index, result in enumerate(results, start=1):
        freqs = "/".join(f"{frequency:g}" for frequency in result.frequencies_mhz)
        passed = "Y" if result.meets_range and result.meets_precision else "N"
        print(
            f"{index:>4} | {freqs:<15} | {result.score:>5.1f} | "
            f"{_m(result.synthetic_range_m):>9} | {_mm(result.combined_precision_m):>10} | "
            f"{_mm(result.beat_noise_m):>10} | {result.min_pair_delta_mhz:>7g} | {passed}"
        )


def _heatmap(args: argparse.Namespace) -> None:
    frequencies = _frequency_grid(
        args.min_frequency_mhz, args.max_frequency_mhz, args.step_mhz
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "f1_mhz",
                "f2_mhz",
                "synthetic_range_m",
                "combined_precision_mm",
                "beat_noise_mm",
                "noise_amplification_factor",
                "robustness",
            ],
        )
        writer.writeheader()
        for i, f1 in enumerate(frequencies):
            for f2 in frequencies[i + 1 :]:
                result = analyze_pair(f1, f2, args.phase_noise)
                writer.writerow(
                    {
                        "f1_mhz": f1,
                        "f2_mhz": f2,
                        "synthetic_range_m": result.synthetic_range_m,
                        "combined_precision_mm": _meters_to_mm(result.combined_precision_m),
                        "beat_noise_mm": _meters_to_mm(result.beat_noise_m),
                        "noise_amplification_factor": result.noise_amplification_factor,
                        "robustness": result.robustness,
                    }
                )
    print(f"Wrote {args.output}")


def _frequency_grid(
    min_frequency_mhz: float, max_frequency_mhz: float, step_mhz: float
) -> list[float]:
    values: list[float] = []
    current = min_frequency_mhz
    epsilon = step_mhz / 1_000_000.0
    while current <= max_frequency_mhz + epsilon:
        values.append(round(current, 9))
        current += step_mhz
    return values


def _m(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4g} m"


def _mm(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 1000.0:.4g} mm"


def _meters_to_mm(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 1000.0


if __name__ == "__main__":
    main()
