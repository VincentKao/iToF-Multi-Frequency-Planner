import unittest

from itof_planner.core import (
    analyze_multi_frequency,
    analyze_pair,
    distance_precision_m,
    search_frequency_sets,
    synthetic_range_m,
    unambiguous_range_m,
)


class CoreMathTest(unittest.TestCase):
    def test_unambiguous_range(self):
        self.assertAlmostEqual(unambiguous_range_m(80), 1.8737, places=3)
        self.assertAlmostEqual(unambiguous_range_m(20), 7.4948, places=3)

    def test_synthetic_range(self):
        self.assertAlmostEqual(synthetic_range_m(80, 70), 14.9896, places=3)
        self.assertAlmostEqual(synthetic_range_m(80, 75), 29.9792, places=3)

    def test_distance_precision(self):
        precision = distance_precision_m(100, 0.01)
        self.assertAlmostEqual(precision * 1000.0, 2.3857, places=3)

    def test_pair_analysis(self):
        result = analyze_pair(80, 75, phase_noise_rad=0.01)
        self.assertEqual(result.robustness, "Low")
        self.assertGreater(result.synthetic_range_m, 29.0)
        self.assertLess(result.combined_precision_m, result.precision_2_m)

    def test_multi_frequency_range_uses_common_repeat(self):
        result = analyze_multi_frequency([20, 60, 100], phase_noise_rad=0.01)
        self.assertAlmostEqual(result.synthetic_range_m, 7.4948, places=3)
        self.assertAlmostEqual(result.min_pair_delta_mhz, 40.0)

    def test_search_returns_ranked_candidates(self):
        results = search_frequency_sets(
            min_frequency_mhz=20,
            max_frequency_mhz=100,
            step_mhz=20,
            count=3,
            max_distance_m=5,
            target_precision_m=0.005,
            phase_noise_rad=0.01,
            limit=3,
        )
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0].meets_range)
        self.assertTrue(results[0].meets_precision)


if __name__ == "__main__":
    unittest.main()
