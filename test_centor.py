"""
Unit Test Suite for Centor and Modified Centor (McIsaac) Score Calculator.
Tests raw Centor scoring, McIsaac age modifiers, diagnostic stewardship thresholds,
antimicrobial recommendations, allergy pathways, batch CSV processing, and CLI interfaces.
"""

import csv
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from centor import (
    assess_row,
    calculate_mcisaac_score,
    calculate_raw_centor,
    calculate_score,
    evaluate_mcisaac,
    get_age_modifier,
    get_antibiotic_regimens,
    process_csv,
    ClinicalAction,
    RiskTier,
)
from cli import main as cli_main


class TestCentorScore(unittest.TestCase):
    def test_centor_score_0(self):
        score = calculate_raw_centor(False, False, False, False)
        self.assertEqual(score, 0)

    def test_centor_score_1(self):
        score = calculate_raw_centor(absence_of_cough=True)
        self.assertEqual(score, 1)

    def test_centor_score_2(self):
        score = calculate_raw_centor(
            absence_of_cough=True,
            tender_anterior_cervical_nodes=True,
        )
        self.assertEqual(score, 2)

    def test_centor_score_3(self):
        score = calculate_raw_centor(
            absence_of_cough=True,
            tender_anterior_cervical_nodes=True,
            tonsillar_exudate_or_swelling=True,
        )
        self.assertEqual(score, 3)

    def test_centor_score_4(self):
        score = calculate_raw_centor(
            absence_of_cough=True,
            tender_anterior_cervical_nodes=True,
            tonsillar_exudate_or_swelling=True,
            history_of_fever_or_temp_gt_38=True,
        )
        self.assertEqual(score, 4)


class TestMcIsaacAgeModifiers(unittest.TestCase):
    def test_age_modifier_child_3_to_14(self):
        for age in [3.0, 5.0, 10.0, 14.0]:
            mod, warn = get_age_modifier(age)
            self.assertEqual(mod, 1)
            self.assertIsNone(warn)

    def test_age_modifier_adult_15_to_44(self):
        for age in [15.0, 25.0, 35.0, 44.0]:
            mod, warn = get_age_modifier(age)
            self.assertEqual(mod, 0)
            self.assertIsNone(warn)

    def test_age_modifier_elderly_45_plus(self):
        for age in [45.0, 50.0, 65.0, 80.0]:
            mod, warn = get_age_modifier(age)
            self.assertEqual(mod, -1)
            self.assertIsNone(warn)

    def test_age_under_3_warning(self):
        mod, warn = get_age_modifier(1.5)
        self.assertEqual(mod, 0)
        self.assertIsNotNone(warn)
        self.assertIn("rare in children < 3 years", warn)

    def test_negative_age_raises_error(self):
        with self.assertRaises(ValueError):
            get_age_modifier(-1.0)

    def test_calculate_mcisaac_score_bounds(self):
        self.assertEqual(calculate_mcisaac_score(0, 50), -1)  # 0 + (-1)
        self.assertEqual(calculate_mcisaac_score(4, 8), 5)    # 4 + (+1)
        with self.assertRaises(ValueError):
            calculate_mcisaac_score(5, 20)


class TestClinicalEvaluationThresholds(unittest.TestCase):
    def test_mcisaac_score_zero_or_negative(self):
        # 60 y/o, raw Centor 0 -> McIsaac -1
        res = evaluate_mcisaac(age_years=60.0)
        self.assertEqual(res.mcisaac_score, -1)
        self.assertEqual(res.risk_tier, RiskTier.VERY_LOW)
        self.assertEqual(res.recommended_action, ClinicalAction.NO_TEST_NO_ABX)
        self.assertEqual(len(res.antibiotic_options), 0)

    def test_mcisaac_score_one(self):
        # 25 y/o, raw Centor 1 -> McIsaac 1
        res = evaluate_mcisaac(absence_of_cough=True, age_years=25.0)
        self.assertEqual(res.mcisaac_score, 1)
        self.assertEqual(res.risk_tier, RiskTier.LOW)
        self.assertEqual(res.recommended_action, ClinicalAction.NO_TEST_NO_ABX)

    def test_mcisaac_score_two(self):
        # 25 y/o, raw Centor 2 -> McIsaac 2
        res = evaluate_mcisaac(
            absence_of_cough=True,
            tender_anterior_cervical_nodes=True,
            age_years=25.0,
        )
        self.assertEqual(res.mcisaac_score, 2)
        self.assertEqual(res.risk_tier, RiskTier.INTERMEDIATE)
        self.assertEqual(res.recommended_action, ClinicalAction.TEST_RADT_OR_CULTURE)
        self.assertTrue(len(res.antibiotic_options) > 0)

    def test_mcisaac_score_three(self):
        # 8 y/o, raw Centor 2 -> McIsaac 3
        res = evaluate_mcisaac(
            absence_of_cough=True,
            tonsillar_exudate_or_swelling=True,
            age_years=8.0,
        )
        self.assertEqual(res.mcisaac_score, 3)
        self.assertEqual(res.risk_tier, RiskTier.HIGH)
        self.assertEqual(res.recommended_action, ClinicalAction.TEST_RADT_OR_CULTURE)

    def test_mcisaac_score_four_or_five(self):
        # 8 y/o, raw Centor 4 -> McIsaac 5
        res = evaluate_mcisaac(
            absence_of_cough=True,
            tender_anterior_cervical_nodes=True,
            tonsillar_exudate_or_swelling=True,
            history_of_fever_or_temp_gt_38=True,
            age_years=8.0,
        )
        self.assertEqual(res.mcisaac_score, 5)
        self.assertEqual(res.risk_tier, RiskTier.VERY_HIGH)
        self.assertEqual(res.recommended_action, ClinicalAction.EMPIRIC_ABX_OR_TEST)

    def test_temperature_celsius_auto_detection(self):
        # Temp 38.5 C sets fever automatically
        res = evaluate_mcisaac(temperature_c=38.5, age_years=25.0)
        self.assertEqual(res.centor_score, 1)

        res_norm = evaluate_mcisaac(temperature_c=36.8, age_years=25.0)
        self.assertEqual(res_norm.centor_score, 0)


class TestAntibioticTherapy(unittest.TestCase):
    def test_first_line_penicillin_adult(self):
        regimens = get_antibiotic_regimens(penicillin_allergic=False, age_years=30)
        drugs = [r["drug"] for r in regimens]
        self.assertTrue(any("Penicillin V" in d for d in drugs))
        self.assertTrue(any("Amoxicillin" in d for d in drugs))

    def test_pediatric_penicillin_dosing(self):
        regimens = get_antibiotic_regimens(penicillin_allergic=False, age_years=6, weight_kg=20)
        self.assertTrue(len(regimens) >= 2)
        pen = next(r for r in regimens if "Penicillin V" in r["drug"])
        self.assertIn("250 mg", pen["dosage"])

    def test_non_severe_penicillin_allergy(self):
        regimens = get_antibiotic_regimens(penicillin_allergic=True, severe_allergy=False, age_years=30)
        drugs = [r["drug"] for r in regimens]
        self.assertTrue(any("Cephalexin" in d or "Cefalexin" in d for d in drugs))
        self.assertTrue(any("Cefadroxil" in d for d in drugs))

    def test_severe_penicillin_allergy(self):
        regimens = get_antibiotic_regimens(penicillin_allergic=True, severe_allergy=True, age_years=30)
        drugs = [r["drug"] for r in regimens]
        self.assertFalse(any("Cephalexin" in d or "Cefalexin" in d for d in drugs))
        self.assertTrue(any("Azithromycin" in d for d in drugs))
        self.assertTrue(any("Clindamycin" in d for d in drugs))


class TestScoreDictAndBatchCSV(unittest.TestCase):
    def test_calculate_score_dict_interface(self):
        row = {
            "absence_of_cough": "1",
            "tender_anterior_cervical_nodes": "true",
            "tonsillar_exudate_or_swelling": "yes",
            "history_of_fever_or_temp_gt_38": "1",
            "age": "10",
        }
        res = calculate_score(row)
        self.assertEqual(res["centor_score"], 4)
        self.assertEqual(res["score"], 5)  # 4 + 1
        self.assertEqual(res["risk_tier"], "VERY_HIGH")
        self.assertEqual(res["recommended_action"], "EMPIRIC_ABX_OR_TEST")

    def test_assess_row_and_process_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = os.path.join(tmpdir, "in.csv")
            out_path = os.path.join(tmpdir, "out.csv")

            with open(in_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["patient_id", "absence_of_cough", "tender_cervical_nodes", "tonsillar_exudate", "fever", "age"])
                writer.writeheader()
                writer.writerow({"patient_id": "P1", "absence_of_cough": "1", "tender_cervical_nodes": "1", "tonsillar_exudate": "1", "fever": "1", "age": "8"})
                writer.writerow({"patient_id": "P2", "absence_of_cough": "0", "tender_cervical_nodes": "0", "tonsillar_exudate": "0", "fever": "0", "age": "50"})

            results = process_csv(in_path, out_path)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["mcisaac_score"], 5)
            self.assertEqual(results[1]["mcisaac_score"], -1)

            with open(out_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]["risk_tier"], "VERY_HIGH")
                self.assertEqual(rows[1]["risk_tier"], "VERY_LOW")


class TestCLI(unittest.TestCase):
    def test_cli_eval_json(self):
        buf = io.StringIO()
        with patch("sys.stdout", new=buf):
            ret = cli_main(["eval", "--no-cough", "--nodes", "--exudate", "--fever", "--age", "8", "--json"])
            self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["mcisaac_score"], 5)
        self.assertEqual(data["recommended_action"], "EMPIRIC_ABX_OR_TEST")

    def test_cli_eval_formatted(self):
        buf = io.StringIO()
        with patch("sys.stdout", new=buf):
            ret = cli_main(["eval", "--no-cough", "--nodes", "--age", "25"])
            self.assertEqual(ret, 0)
        output = buf.getvalue()
        self.assertIn("Raw Centor Score (0-4):       2 / 4", output)
        self.assertIn("McIsaac Score (-1 to 5):      2", output)
        self.assertIn("RAPID ANTIGEN TEST", output)


if __name__ == "__main__":
    unittest.main()
