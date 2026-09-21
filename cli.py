#!/usr/bin/env python3
"""Command-line interface for the Centor/McIsaac score calculator."""

from __future__ import annotations

import argparse
import json
import sys

from centor import evaluate_mcisaac, process_csv


def format_clinical_report(res: dict) -> str:
    """Render a concise, text-only clinical decision-support report."""
    score = res.get("score", res.get("mcisaac_score"))
    lines = [
        "=" * 68,
        "CENTOR / MODIFIED CENTOR (McISAAC) PHARYNGITIS SCORE",
        "Risk stratification only — diagnostic testing confirms GAS.",
        "=" * 68,
        f"Raw Centor score:     {res.get('centor_score')} / 4",
        f"McIsaac score:        {score}",
        f"Validation estimate:   {res.get('strep_probability') or res.get('strep_probability_pct')}",
        f"Risk tier:             {res.get('risk_tier')}",
        "",
        "Guidance:",
        f"  {res.get('clinical_guidance', '')}",
    ]

    warnings = res.get("warnings", [])
    if warnings:
        lines.append("\nNotes:")
        lines.extend(f"  - {warning}" for warning in warnings)

    antibiotics = res.get("antibiotics", []) or res.get("antibiotic_options", [])
    if antibiotics:
        lines.append("\nReference regimens for confirmed GAS:")
        for item in antibiotics:
            lines.append(
                f"  - {item['drug']}: {item['dosage']} — {item['duration']}"
            )
            if item.get("notes"):
                lines.append(f"    {item['notes']}")

    lines.extend(["", "Use local guidelines and patient-specific clinical judgment.", "=" * 68])
    return "\n".join(lines)


def _prompt_required_float(message: str) -> float:
    while True:
        raw = input(f"{message}: ").strip()
        try:
            value = float(raw)
        except ValueError:
            print("Enter a numeric value.")
            continue
        if value < 0:
            print("Value cannot be negative.")
            continue
        return value


def _prompt_yes_no(message: str) -> bool:
    while True:
        answer = input(f"{message} (y/n): ").strip().lower()
        if answer in {"y", "yes", "1", "true"}:
            return True
        if answer in {"n", "no", "0", "false"}:
            return False
        print("Enter y or n.")


def interactive_mode() -> int:
    print("Centor / Modified Centor (McIsaac) pharyngitis score")
    print("This score supports testing decisions; it does not diagnose GAS.\n")

    age = _prompt_required_float("Age in years")
    fever = _prompt_yes_no("History of fever or temperature ≥38.0°C")
    no_cough = _prompt_yes_no("Absence of cough")
    nodes = _prompt_yes_no("Tender/swollen anterior cervical nodes")
    exudate = _prompt_yes_no("Tonsillar exudate or swelling")
    clear_viral = _prompt_yes_no("Clear viral features (e.g., rhinorrhea, oral ulcers, hoarseness)")
    high_risk = _prompt_yes_no("High-risk context (e.g., GAS household exposure or prior rheumatic fever)")

    result = evaluate_mcisaac(
        absence_of_cough=no_cough,
        tender_anterior_cervical_nodes=nodes,
        tonsillar_exudate_or_swelling=exudate,
        history_of_fever_or_temp_gt_38=fever,
        age_years=age,
        clear_viral_features=clear_viral,
        high_risk_context=high_risk,
    )
    print("\n" + format_clinical_report(result.to_dict()))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="centor-mcisaac-score",
        description="Centor and Modified Centor (McIsaac) pharyngitis risk calculator",
    )
    subparsers = parser.add_subparsers(dest="command")

    for command in ("eval", "single"):
        item = subparsers.add_parser(command, help="Evaluate one sore-throat case")
        item.add_argument("--age", type=float, required=True, help="Patient age in years")
        item.add_argument("--temp", "--temperature", type=float, default=None, help="Measured temperature in Celsius")
        item.add_argument("--fever", action="store_true", help="History of fever or temperature ≥38.0°C")
        item.add_argument("--no-cough", "--cough-absent", action="store_true", help="Absence of cough")
        item.add_argument("--nodes", "--tender-nodes", action="store_true", help="Tender anterior cervical nodes")
        item.add_argument("--exudate", "--tonsil-swelling", action="store_true", help="Tonsillar exudate or swelling")
        item.add_argument("--viral-features", action="store_true", help="Clear features suggesting viral pharyngitis")
        item.add_argument("--high-risk", action="store_true", help="High-risk GAS context despite a low score")
        item.add_argument("--gas-test-result", choices=["positive", "negative_radt", "negative_culture", "negative_naat"], default=None)
        item.add_argument("--weight", type=float, default=None, help="Patient weight in kg, used only for confirmed-GAS reference regimens")
        item.add_argument("--penicillin-allergy", action="store_true")
        item.add_argument("--severe-allergy", action="store_true", help="Immediate/severe penicillin hypersensitivity")
        item.add_argument("--json", action="store_true", help="Output JSON")

    subparsers.add_parser("interactive", help="Run a guided questionnaire")

    batch = subparsers.add_parser("batch", help="Batch-evaluate CSV records")
    batch.add_argument("-i", "--input", required=True, help="Input CSV path")
    batch.add_argument("-o", "--output", default="scored_mcisaac_batch.csv", help="Output CSV path")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "interactive":
        return interactive_mode()
    if args.command in {"eval", "single"}:
        try:
            result = evaluate_mcisaac(
                absence_of_cough=args.no_cough,
                tender_anterior_cervical_nodes=args.nodes,
                tonsillar_exudate_or_swelling=args.exudate,
                history_of_fever_or_temp_gt_38=args.fever,
                age_years=args.age,
                temperature_c=args.temp,
                penicillin_allergic=args.penicillin_allergy,
                severe_allergy=args.severe_allergy,
                weight_kg=args.weight,
                gas_test_result=args.gas_test_result,
                clear_viral_features=args.viral_features,
                high_risk_context=args.high_risk,
            )
        except ValueError as exc:
            parser.error(str(exc))

        payload = result.to_dict()
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(format_clinical_report(payload))
        return 0
    if args.command == "batch":
        try:
            results = process_csv(args.input, args.output)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print(f"Processed {len(results)} records -> {args.output}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
