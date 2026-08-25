#!/usr/bin/env python3
"""
Command Line Interface for Centor & McIsaac Strep Score Calculator
Provides interactive clinical consultation, single-case evaluation, batch CSV processing, and JSON output.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from centor import (
    assess_row,
    calculate_score,
    evaluate_mcisaac,
    process_csv,
    ClinicalAction,
    RiskTier,
)


def format_clinical_report(res: dict) -> str:
    """Renders formatted clinical decision support report."""
    lines = []
    lines.append("=" * 72)
    lines.append("  CENTOR & MCISAAC (MODIFIED CENTOR) STREP PHARYNGITIS EVALUATION")
    lines.append("  Guidelines: IDSA 2012 / McIsaac et al. (1998, 2004) / Centor (1981)")
    lines.append("=" * 72)

    warnings = res.get("warnings", [])
    if warnings:
        lines.append("\n  [!] CLINICAL WARNING:")
        for w in warnings:
            lines.append(f"      * {w}")

    score = res.get("score") if "score" in res else res.get("mcisaac_score")
    centor = res.get("centor_score")
    strep_prob = res.get("strep_probability") or res.get("strep_probability_pct")
    tier = res.get("risk_tier") or str(res.get("tier", "")).upper()
    action = res.get("recommended_action")

    lines.append(f"\n  [Scoring Breakdown]")
    lines.append(f"  * Raw Centor Score (0-4):       {centor} / 4")
    lines.append(f"  * McIsaac Score (-1 to 5):      {score}")
    lines.append(f"  * Estimated GAS Risk:           {strep_prob}")
    lines.append(f"  * Risk Classification:          [{tier}]")

    detail = res.get("detail", {})
    if detail:
        lines.append(f"\n  [Criteria Met]:")
        for k, v in detail.items():
            lines.append(f"    - {k}: {v:+d}" if isinstance(v, int) else f"    - {k}: {v}")

    action_labels = {
        "NO_TEST_NO_ABX": "NO TESTING & NO ANTIBIOTICS (Symptomatic Care Only)",
        "TEST_RADT_OR_CULTURE": "RAPID ANTIGEN TEST (RADT) OR CULTURE (Treat if Positive)",
        "EMPIRIC_ABX_OR_TEST": "EMPIRIC ANTIBIOTICS OR RADT WITH IMMEDIATE THERAPY",
    }
    lines.append(f"\n  [Clinical Recommendation]: [{action_labels.get(action, action)}]")
    lines.append(f"  {res.get('clinical_guidance', '')}")

    antibiotics = res.get("antibiotics", []) or res.get("antibiotic_options", [])
    if antibiotics:
        lines.append(f"\n  [Guideline Antimicrobial Options (IDSA / AAP)]:")
        for idx, abx in enumerate(antibiotics, start=1):
            drug = abx.get("drug") or abx.get("drug_name")
            dose = abx.get("dosage") or abx.get("dose")
            dur = abx.get("duration")
            pref = abx.get("preference") or abx.get("indication", "")
            notes = abx.get("notes", "")
            lines.append(f"    {idx}. {drug} ({pref})")
            lines.append(f"       Regimen:  {dose} for {dur}")
            if notes:
                lines.append(f"       Notes:    {notes}")

    symptomatic = res.get("symptomatic_measures", [])
    if symptomatic:
        lines.append(f"\n  [Symptomatic Relief & Supportive Care]:")
        for sym in symptomatic:
            lines.append(f"    - {sym}")

    lines.append("=" * 72)
    return "\n".join(lines)


def interactive_mode():
    """Interactive CLI consultation."""
    print("=" * 72)
    print("  MCISAAC / CENTOR SORE THROAT ASSESSMENT - INTERACTIVE CONSULTATION")
    print("=" * 72)

    def prompt_yes_no(msg: str) -> bool:
        while True:
            ans = input(f"{msg} (y/n): ").strip().lower()
            if ans in ("y", "yes", "1", "t", "true"):
                return True
            if ans in ("n", "no", "0", "f", "false"):
                return False
            print("Please enter 'y' for yes or 'n' for no.")

    def prompt_float(msg: str, default: float) -> float:
        while True:
            val = input(f"{msg} [{default}]: ").strip()
            if not val:
                return default
            try:
                num = float(val)
                if num < 0:
                    print("Value cannot be negative.")
                    continue
                return num
            except ValueError:
                print("Invalid number, please try again.")

    print("\n--- 1. Patient Demographics ---")
    age = prompt_float("Patient age in years", 25.0)
    weight = prompt_float("Patient weight in kg (for pediatric dosing)", 70.0)

    print("\n--- 2. Centor Criteria ---")
    fever = prompt_yes_no("History of fever OR measured temperature > 38.0°C (100.4°F)?")
    no_cough = prompt_yes_no("Absence of cough (patient does NOT have a cough)?")
    nodes = prompt_yes_no("Tender or swollen anterior cervical lymph nodes?")
    exudate = prompt_yes_no("Tonsillar exudates or swelling / tonsillitis?")

    print("\n--- 3. Penicillin Allergy Status ---")
    pen_allergy = prompt_yes_no("Does the patient have an allergy to penicillin?")
    severe_allergy = False
    if pen_allergy:
        severe_allergy = prompt_yes_no("Was the reaction severe (anaphylaxis, hives, angioedema, airway swelling)?")

    result = evaluate_mcisaac(
        absence_of_cough=no_cough,
        tender_anterior_cervical_nodes=nodes,
        tonsillar_exudate_or_swelling=exudate,
        history_of_fever_or_temp_gt_38=fever,
        age_years=age,
        weight_kg=weight,
        penicillin_allergic=pen_allergy,
        severe_allergy=severe_allergy,
    )

    print("\n" + format_clinical_report(result.to_dict()))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="centor-mcisaac-score",
        description="Centor and Modified Centor (McIsaac) Strep Score Calculator",
    )
    subparsers = parser.add_subparsers(dest="command")

    # eval / single
    for cmd_name in ("eval", "single"):
        p_s = subparsers.add_parser(cmd_name, help="Evaluate a single sore throat case")
        p_s.add_argument("--age", type=float, default=25.0, help="Patient age in years")
        p_s.add_argument("--temp", "--temperature", type=float, default=None, help="Measured oral/tympanic temperature in Celsius")
        p_s.add_argument("--fever", action="store_true", help="History of fever or temp > 38.0 C")
        p_s.add_argument("--no-cough", "--cough-absent", action="store_true", help="Absence of cough")
        p_s.add_argument("--nodes", "--tender-nodes", action="store_true", help="Tender anterior cervical lymphadenopathy")
        p_s.add_argument("--exudate", "--tonsil-swelling", action="store_true", help="Tonsillar exudates or tonsillar swelling")
        p_s.add_argument("--weight", type=float, default=None, help="Patient weight in kg")
        p_s.add_argument("--penicillin-allergy", action="store_true", help="Patient is allergic to penicillin")
        p_s.add_argument("--severe-allergy", action="store_true", help="Severe/anaphylactic penicillin allergy")
        p_s.add_argument("--json", action="store_true", help="Output results as JSON")

    # interactive
    subparsers.add_parser("interactive", help="Start guided interactive consultation questionnaire")

    # batch
    p_b = subparsers.add_parser("batch", help="Batch evaluate CSV records")
    p_b.add_argument("-i", "--input", required=True, help="Input CSV file path")
    p_b.add_argument("-o", "--output", default="scored_mcisaac_batch.csv", help="Output CSV file path")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "interactive" or (args.command is None and len(sys.argv) == 1):
        interactive_mode()
        return 0

    if args.command in ("eval", "single"):
        res = evaluate_mcisaac(
            absence_of_cough=args.no_cough,
            tender_anterior_cervical_nodes=args.nodes,
            tonsillar_exudate_or_swelling=args.exudate,
            history_of_fever_or_temp_gt_38=args.fever,
            age_years=args.age,
            temperature_c=args.temp,
            penicillin_allergic=args.penicillin_allergy,
            severe_allergy=args.severe_allergy,
            weight_kg=args.weight,
        )
        res_dict = res.to_dict()
        if args.json:
            print(json.dumps(res_dict, indent=2))
        else:
            print(format_clinical_report(res_dict))
        return 0

    if args.command == "batch":
        res_list = process_csv(args.input, args.output)
        print(f"Processed {len(res_list)} records -> {args.output}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
