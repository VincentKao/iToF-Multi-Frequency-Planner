import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class MbtCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "itof_planner.cli", *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_mbt_cli_001_single_command_outputs_range_and_precision(self):
        result = self.run_cli("single", "80", "--phase-noise", "0.01")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Unambiguous range", result.stdout)
        self.assertIn("Distance precision", result.stdout)
        self.assertIn("1.874 m", result.stdout)
        self.assertIn("2.982 mm", result.stdout)

    def test_mbt_cli_002_pair_command_outputs_pair_metrics(self):
        result = self.run_cli("pair", "80", "75", "--phase-noise", "0.01")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Synthetic range", result.stdout)
        self.assertIn("Beat noise", result.stdout)
        self.assertIn("Unwrap robustness", result.stdout)
        self.assertIn("Low", result.stdout)

    def test_mbt_cli_003_multi_command_outputs_multi_metrics(self):
        result = self.run_cli("multi", "20", "60", "100", "--phase-noise", "0.01")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Pair synthetic ranges", result.stdout)
        self.assertIn("Combined precision", result.stdout)
        self.assertIn("20/60 MHz", result.stdout)

    def test_mbt_cli_004_search_command_outputs_three_ranked_candidates(self):
        result = self.run_cli(
            "search",
            "--min",
            "20",
            "--max",
            "120",
            "--step",
            "20",
            "--count",
            "3",
            "--max-distance",
            "5",
            "--target-precision-mm",
            "5",
            "--phase-noise",
            "0.01",
            "--top",
            "3",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [
            line
            for line in result.stdout.splitlines()
            if line.strip() and line.lstrip()[0].isdigit()
        ]
        self.assertEqual(len(rows), 3)
        self.assertIn("20/60/100", result.stdout)

    def test_mbt_cli_005_heatmap_command_writes_csv_with_expected_header(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pair_heatmap.csv"
            result = self.run_cli(
                "heatmap",
                "--min",
                "20",
                "--max",
                "40",
                "--step",
                "10",
                "--phase-noise",
                "0.01",
                "--output",
                str(output),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists())
            with output.open(newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                header = next(reader)
                rows = list(reader)

        self.assertEqual(
            header,
            [
                "f1_mhz",
                "f2_mhz",
                "synthetic_range_m",
                "combined_precision_mm",
                "beat_noise_mm",
                "noise_amplification_factor",
                "robustness",
            ],
        )
        self.assertEqual(len(rows), 3)

    def test_mbt_cli_006_pair_command_rejects_equal_frequencies(self):
        result = self.run_cli("pair", "80", "80")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("frequencies must be distinct", result.stderr)

    def test_inv_12_cli_single_output_matches_core_format_tolerance(self):
        result = self.run_cli("single", "20", "--phase-noise", "0.01")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("7.495 m", result.stdout)
        self.assertIn("11.93 mm", result.stdout)


if __name__ == "__main__":
    unittest.main()
