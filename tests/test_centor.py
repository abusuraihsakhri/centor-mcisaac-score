import csv
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from centor import (
    ClinicalAction,
    RiskTier,
    calculate_mcisaac_score,
    calculate_raw_centor,
    calculate_score,
    evaluate_mcisaac,
    get_age_modifier,
    get_antibiotic_regimens,
    process_csv,
)
from cli import main as cli_main


class TestCentorScoring(unittest.TestCase):
    def test_all_four_criteria(self):
        self.assertEqual(calculate_raw_centor(True, True, True, True), 4)

    def test_age_modifiers(self):
        self.assertEqual(get_age_modifier(3)[0], 1)
        self.assertEqual(get_age_modifier(14)[0], 1)
        self.assertEqual(get_age_modifier(15)[0], 0)
        self.assertEqual(get_age_modifier(44)[0], 0)
        self.assertEqual(get_age_modifier(45)[0], -1)

    def test_under_three_not_applicable_warning(self):
        modifier, warning = get_age_modifier(2)
        self.assertEqual(modifier, 0)
        self.assertIn("not intended", warning)

    def test_nonfinite_age_rejected(self):
        for value in [float("nan"), float("inf"), float("-inf")]:
            with self.assertRaises(ValueError):
                get_age_modifier(value)

    def test_mcisaac_bounds(self):
        self.assertEqual(calculate_mcisaac_score(0, 50), -1)
        self.assertEqual(calculate_mcisaac_score(4, 8), 5)
        with self.assertRaises(ValueError):
            calculate_mcisaac_score(5, 20)
        with self.assertRaises(ValueError):
            calculate_mcisaac_score(2.5, 20)


class TestClinicalGuidance(unittest.TestCase):
    def test_high_score_requires_testing_not_empiric_antibiotics(self):
        result = evaluate_mcisaac(
            absence_of_cough=True,
            tender_anterior_cervical_nodes=True,
            tonsillar_exudate_or_swelling=True,
            history_of_fever_or_temp_gt_38=True,
            age_years=8,
        )
        self.assertEqual(result.mcisaac_score, 5)
        self.assertEqual(result.risk_tier, RiskTier.VERY_HIGH)
        self.assertEqual(result.recommended_action, ClinicalAction.TEST_RADT_OR_CULTURE)
        self.assertEqual(result.antibiotic_options, [])
        self.assertIn("Do not prescribe antibiotics", result.clinical_guidance)

    def test_positive_test_releases_reference_regimens(self):
        result = evaluate_mcisaac(age_years=25, gas_test_result="positive")
        self.assertGreaterEqual(len(result.antibiotic_options), 3)
        self.assertIn("confirmed", result.clinical_guidance.lower())

    def test_negative_radt_child_requires_backup_culture(self):
        result = evaluate_mcisaac(age_years=8, gas_test_result="negative_radt")
        self.assertIn("back-up throat culture", result.clinical_guidance)
        self.assertEqual(result.antibiotic_options, [])

    def test_negative_radt_adult_does_not_routinely_require_culture(self):
        result = evaluate_mcisaac(age_years=30, gas_test_result="negative_radt")
        self.assertIn("generally not indicated", result.clinical_guidance)

    def test_clear_viral_features_override_score_testing(self):
        result = evaluate_mcisaac(
            absence_of_cough=True,
            tender_anterior_cervical_nodes=True,
            tonsillar_exudate_or_swelling=True,
            history_of_fever_or_temp_gt_38=True,
            age_years=30,
            clear_viral_features=True,
        )
        self.assertEqual(result.recommended_action, ClinicalAction.NO_TEST_NO_ABX)
        self.assertIn("viral", result.clinical_guidance.lower())

    def test_high_risk_context_overrides_low_score(self):
        result = evaluate_mcisaac(age_years=30, high_risk_context=True)
        self.assertEqual(result.mcisaac_score, 0)
        self.assertEqual(result.recommended_action, ClinicalAction.TEST_RADT_OR_CULTURE)

    def test_under_three_score_marked_not_applicable(self):
        result = evaluate_mcisaac(age_years=2, absence_of_cough=True)
        self.assertFalse(result.score_applicable)
        self.assertEqual(result.recommended_action, ClinicalAction.NO_TEST_NO_ABX)

    def test_temperature_sets_fever(self):
        self.assertEqual(evaluate_mcisaac(age_years=25, temperature_c=38.0).centor_score, 1)
        self.assertEqual(evaluate_mcisaac(age_years=25, temperature_c=37.9).centor_score, 0)

    def test_validation_estimate_normalizes_extreme_scores(self):
        low = evaluate_mcisaac(age_years=50)
        high = evaluate_mcisaac(
            age_years=8,
            absence_of_cough=True,
            tender_anterior_cervical_nodes=True,
            tonsillar_exudate_or_swelling=True,
            history_of_fever_or_temp_gt_38=True,
        )
        self.assertEqual(low.strep_probability_pct, "8% (95% CI 8–9%)")
        self.assertEqual(high.strep_probability_pct, "55% (95% CI 55–56%)")


class TestAntibioticReference(unittest.TestCase):
    def test_pediatric_penicillin_v_dose_is_fixed_guideline_dose(self):
        regimens = get_antibiotic_regimens(age_years=6, weight_kg=10)
        penicillin = next(r for r in regimens if r["drug"] == "Penicillin V")
        self.assertIn("250 mg", penicillin["dosage"])
        self.assertNotIn("125 mg", penicillin["dosage"])

    def test_adult_penicillin_v_no_500mg_tid(self):
        regimens = get_antibiotic_regimens(age_years=30)
        penicillin = next(r for r in regimens if r["drug"] == "Penicillin V")
        self.assertIn("500 mg orally twice daily", penicillin["dosage"])
        self.assertNotIn("three times", penicillin["dosage"])

    def test_severe_allergy_implies_no_cephalosporin(self):
        regimens = get_antibiotic_regimens(severe_allergy=True, age_years=30)
        drugs = {r["drug"] for r in regimens}
        self.assertNotIn("Cephalexin", drugs)
        self.assertNotIn("Cefadroxil", drugs)
        self.assertIn("Azithromycin", drugs)

    def test_invalid_weight_rejected(self):
        with self.assertRaises(ValueError):
            get_antibiotic_regimens(age_years=8, weight_kg=0)


class TestDictionaryAndCsv(unittest.TestCase):
    def test_dictionary_interface(self):
        result = calculate_score(
            {
                "absence_of_cough": "yes",
                "tender_cervical_nodes": "1",
                "tonsillar_exudate": "true",
                "fever": "1",
                "age": "10",
            }
        )
        self.assertEqual(result["score"], 5)
        self.assertEqual(result["recommended_action"], "TEST_RADT_OR_CULTURE")
        self.assertEqual(result["antibiotics"], [])

    def test_missing_age_rejected_in_dictionary_input(self):
        with self.assertRaisesRegex(ValueError, "Missing required field"):
            calculate_score({"fever": "1"})

    def test_invalid_boolean_rejected(self):
        with self.assertRaisesRegex(ValueError, "unrecognized boolean"):
            calculate_score({"age": "20", "fever": "maybe"})

    def test_invalid_numeric_rejected_not_defaulted(self):
        with self.assertRaisesRegex(ValueError, "must be numeric"):
            calculate_score({"age": "adult", "fever": "1"})

    def test_batch_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "input.csv")
            target = os.path.join(tmpdir, "output.csv")
            with open(source, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["patient_id", "fever", "age"])
                writer.writeheader()
                writer.writerow({"patient_id": "P1", "fever": "1", "age": "8"})
                writer.writerow({"patient_id": "P2", "fever": "0", "age": "50"})
            results = process_csv(source, target)
            self.assertEqual(len(results), 2)
            self.assertTrue(os.path.exists(target))

    def test_batch_error_reports_row(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "input.csv")
            target = os.path.join(tmpdir, "output.csv")
            with open(source, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["patient_id", "fever", "age"])
                writer.writeheader()
                writer.writerow({"patient_id": "P1", "fever": "maybe", "age": "8"})
            with self.assertRaisesRegex(ValueError, "CSV row 2"):
                process_csv(source, target)


class TestCli(unittest.TestCase):
    def test_eval_json(self):
        buffer = io.StringIO()
        with patch("sys.stdout", new=buffer):
            code = cli_main(["eval", "--age", "8", "--fever", "--exudate", "--nodes", "--no-cough", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["mcisaac_score"], 5)
        self.assertEqual(payload["recommended_action"], "TEST_RADT_OR_CULTURE")
        self.assertEqual(payload["antibiotic_options"], [])

    def test_positive_test_cli_shows_treatment_reference(self):
        buffer = io.StringIO()
        with patch("sys.stdout", new=buffer):
            code = cli_main(["eval", "--age", "25", "--gas-test-result", "positive"])
        self.assertEqual(code, 0)
        self.assertIn("Reference regimens for confirmed GAS", buffer.getvalue())

    def test_eval_requires_age(self):
        with self.assertRaises(SystemExit):
            cli_main(["eval", "--fever"])


if __name__ == "__main__":
    unittest.main()
