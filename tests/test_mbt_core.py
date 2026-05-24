import unittest

from itof_planner.core import (
    analyze_frequency,
    analyze_multi_frequency,
    analyze_pair,
    distance_precision_m,
    search_frequency_sets,
    synthetic_range_m,
    unambiguous_range_m,
)


class MbtCoreFormulaTest(unittest.TestCase):
    def test_mbt_core_001_single_80mhz_range(self):
        result = analyze_frequency(80)

        self.assertAlmostEqual(result.unambiguous_range_m, 1.8737, places=3)
        self.assertIsNone(result.precision_m)

    def test_mbt_core_002_single_20mhz_range(self):
        result = analyze_frequency(20)

        self.assertAlmostEqual(result.unambiguous_range_m, 7.4948, places=3)

    def test_mbt_core_003_single_100mhz_precision(self):
        result = analyze_frequency(100, phase_noise_rad=0.01)

        self.assertAlmostEqual(result.precision_m * 1000.0, 2.3857, places=3)

    def test_mbt_core_004_pair_80_70mhz_synthetic_range(self):
        result = analyze_pair(80, 70)

        self.assertAlmostEqual(result.synthetic_range_m, 14.9896, places=3)

    def test_mbt_core_005_pair_80_75mhz_synthetic_range(self):
        result = analyze_pair(80, 75, phase_noise_rad=0.01)

        self.assertAlmostEqual(result.synthetic_range_m, 29.9792, places=3)
        self.assertEqual(result.robustness, "Low")

    def test_mbt_core_006_pair_synthetic_range_is_symmetric(self):
        forward = analyze_pair(80, 75)
        reverse = analyze_pair(75, 80)

        self.assertAlmostEqual(
            forward.synthetic_range_m, reverse.synthetic_range_m, places=9
        )
        self.assertAlmostEqual(
            forward.noise_amplification_factor,
            reverse.noise_amplification_factor,
            places=9,
        )

    def test_mbt_core_007_multi_20_60_100mhz_analysis(self):
        result = analyze_multi_frequency([20, 60, 100], phase_noise_rad=0.01)

        self.assertAlmostEqual(result.synthetic_range_m, 7.4948, places=3)
        self.assertAlmostEqual(result.min_pair_delta_mhz, 40.0, places=9)
        self.assertAlmostEqual(result.combined_precision_m * 1000.0, 2.016, places=3)
        self.assertEqual(len(result.pair_ranges_m), 3)

    def test_mbt_core_008_search_nominal_design_case(self):
        results = search_frequency_sets(
            min_frequency_mhz=20,
            max_frequency_mhz=120,
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
        self.assertIn((20, 60, 100), [item.frequencies_mhz for item in results])


class MbtValidationTest(unittest.TestCase):
    def test_mbt_val_001_reject_zero_single_frequency(self):
        with self.assertRaises(ValueError):
            analyze_frequency(0)

    def test_mbt_val_002_reject_negative_single_frequency(self):
        with self.assertRaises(ValueError):
            analyze_frequency(-10)

    def test_mbt_val_003_reject_equal_pair_frequency(self):
        with self.assertRaises(ValueError):
            analyze_pair(80, 80)

    def test_mbt_val_004_reject_negative_pair_frequency(self):
        with self.assertRaises(ValueError):
            analyze_pair(80, -10)

    def test_mbt_val_005_reject_single_item_multi_frequency(self):
        with self.assertRaises(ValueError):
            analyze_multi_frequency([80])

    def test_mbt_val_006_reject_duplicate_multi_frequency(self):
        with self.assertRaises(ValueError):
            analyze_multi_frequency([20, 60, 60])

    def test_mbt_val_007_reject_search_min_greater_than_max(self):
        with self.assertRaises(ValueError):
            search_frequency_sets(120, 20, 20, 3, 5, 0.005, 0.01)

    def test_mbt_val_008_reject_search_zero_step(self):
        with self.assertRaises(ValueError):
            search_frequency_sets(20, 120, 0, 3, 5, 0.005, 0.01)

    def test_mbt_val_009_reject_zero_target_precision(self):
        with self.assertRaises(ValueError):
            search_frequency_sets(20, 120, 20, 3, 5, 0, 0.01)

    def test_mbt_val_010_reject_negative_phase_noise(self):
        with self.assertRaises(ValueError):
            search_frequency_sets(20, 120, 20, 3, 5, 0.005, -0.01)


class MbtInvariantTest(unittest.TestCase):
    def test_inv_01_range_decreases_when_frequency_increases(self):
        self.assertGreater(unambiguous_range_m(20), unambiguous_range_m(80))

    def test_inv_02_precision_decreases_when_frequency_increases(self):
        self.assertGreater(
            distance_precision_m(20, 0.01), distance_precision_m(100, 0.01)
        )

    def test_inv_03_precision_scales_linearly_with_phase_noise(self):
        low_noise = distance_precision_m(80, 0.01)
        high_noise = distance_precision_m(80, 0.02)

        self.assertAlmostEqual(high_noise, low_noise * 2.0, places=12)

    def test_inv_05_synthetic_range_increases_when_delta_decreases(self):
        self.assertGreater(synthetic_range_m(80, 75), synthetic_range_m(80, 70))

    def test_inv_08_combined_precision_beats_best_single_precision(self):
        result = analyze_multi_frequency([20, 60, 100], phase_noise_rad=0.01)
        single_precisions = [
            distance_precision_m(frequency, 0.01) for frequency in [20, 60, 100]
        ]

        self.assertLessEqual(result.combined_precision_m, min(single_precisions))

    def test_inv_09_min_pair_delta_is_minimum_absolute_delta(self):
        result = analyze_multi_frequency([20, 60, 100], phase_noise_rad=0.01)

        self.assertEqual(result.min_pair_delta_mhz, 40)

    def test_inv_10_search_output_respects_limit(self):
        results = search_frequency_sets(20, 120, 20, 3, 5, 0.005, 0.01, limit=2)

        self.assertLessEqual(len(results), 2)

    def test_inv_11_search_output_is_sorted_by_model_key(self):
        results = search_frequency_sets(20, 120, 20, 3, 5, 0.005, 0.01, limit=10)
        keys = [
            (
                item.meets_range,
                item.meets_precision,
                item.score,
                -item.beat_noise_m,
            )
            for item in results
        ]

        self.assertEqual(keys, sorted(keys, reverse=True))


if __name__ == "__main__":
    unittest.main()
