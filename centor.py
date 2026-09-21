"""Centor and Modified Centor (McIsaac) score utilities.

The score is used as a clinical risk-stratification aid for patients with sore
throat. It does not diagnose group A streptococcal (GAS) pharyngitis and must
not be used by itself to justify antibiotic treatment.
"""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ClinicalAction(str, Enum):
    """High-level action returned by the score engine.

    EMPIRIC_ABX_OR_TEST is retained as a deprecated compatibility value for
    callers that imported it from older releases; the evaluator no longer
    emits it.
    """

    NO_TEST_NO_ABX = "NO_TEST_NO_ABX"
    TEST_RADT_OR_CULTURE = "TEST_RADT_OR_CULTURE"
    EMPIRIC_ABX_OR_TEST = "EMPIRIC_ABX_OR_TEST"


class RiskTier(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    INTERMEDIATE = "INTERMEDIATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass
class CentorCriteriaDetail:
    absence_of_cough: bool
    tender_anterior_cervical_nodes: bool
    tonsillar_exudate_or_swelling: bool
    history_of_fever_or_temp_gt_38: bool
    raw_centor_score: int


@dataclass
class McIsaacResult:
    centor_score: int
    age_years: float
    age_modifier: int
    mcisaac_score: int
    strep_probability_pct: str
    risk_numeric: float
    risk_tier: RiskTier
    recommended_action: ClinicalAction
    clinical_guidance: str
    score_applicable: bool = True
    gas_test_result: Optional[str] = None
    antibiotic_options: List[Dict[str, str]] = field(default_factory=list)
    symptomatic_measures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    criteria_breakdown: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["risk_tier"] = self.risk_tier.value
        data["recommended_action"] = self.recommended_action.value
        return data


def _require_finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return value


def calculate_raw_centor(
    absence_of_cough: bool = False,
    tender_anterior_cervical_nodes: bool = False,
    tonsillar_exudate_or_swelling: bool = False,
    history_of_fever_or_temp_gt_38: bool = False,
) -> int:
    """Compute the original four-item Centor score (0 to 4)."""
    return sum(
        bool(value)
        for value in (
            absence_of_cough,
            tender_anterior_cervical_nodes,
            tonsillar_exudate_or_swelling,
            history_of_fever_or_temp_gt_38,
        )
    )


def get_age_modifier(age_years: float) -> Tuple[int, Optional[str]]:
    """Return the McIsaac age modifier and any applicability warning."""
    age_years = _require_finite(age_years, "Age")
    if age_years < 0:
        raise ValueError(f"Age cannot be negative: {age_years}")

    if age_years < 3:
        return 0, (
            "The McIsaac score is not intended for children under 3 years; "
            "GAS pharyngitis is uncommon and may present atypically in this age group."
        )
    if age_years <= 14:
        return 1, None
    if age_years <= 44:
        return 0, None
    return -1, None


def calculate_mcisaac_score(centor_score: int, age_years: float) -> int:
    """Calculate the composite McIsaac score (-1 to 5 before normalization)."""
    if isinstance(centor_score, bool) or not isinstance(centor_score, int):
        raise ValueError("Centor score must be an integer from 0 to 4")
    if not 0 <= centor_score <= 4:
        raise ValueError(f"Centor score must be between 0 and 4, got: {centor_score}")
    modifier, _ = get_age_modifier(age_years)
    return centor_score + modifier


def _probability_for_score(score: int) -> Tuple[str, float, RiskTier]:
    """Map McIsaac score to Fine et al. 2012 validation prevalence estimates.

    Fine et al. normalized scores -1 and 5 to 0 and 4, respectively. The
    returned value is therefore an observed test-positivity estimate from that
    validation cohort, not an individual diagnostic probability.
    """
    normalized = min(4, max(0, score))
    mapping = {
        0: ("8% (95% CI 8–9%)", 8.0, RiskTier.VERY_LOW),
        1: ("14% (95% CI 13–14%)", 14.0, RiskTier.LOW),
        2: ("23% (95% CI 23–23%)", 23.0, RiskTier.INTERMEDIATE),
        3: ("37% (95% CI 37–37%)", 37.0, RiskTier.HIGH),
        4: ("55% (95% CI 55–56%)", 55.0, RiskTier.VERY_HIGH),
    }
    return mapping[normalized]


def _normalize_test_result(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "": None,
        "not_tested": None,
        "unknown": None,
        "positive": "positive",
        "positive_radt": "positive",
        "positive_culture": "positive",
        "positive_naat": "positive",
        "negative": "negative_radt",
        "negative_radt": "negative_radt",
        "negative_culture": "negative_culture",
        "negative_naat": "negative_naat",
    }
    if normalized not in aliases:
        raise ValueError(
            "gas_test_result must be one of: positive, negative_radt, "
            "negative_culture, negative_naat, or omitted"
        )
    return aliases[normalized]


def get_antibiotic_regimens(
    penicillin_allergic: bool = False,
    severe_allergy: bool = False,
    age_years: Optional[float] = None,
    weight_kg: Optional[float] = None,
) -> List[Dict[str, str]]:
    """Return CDC-listed regimens for confirmed GAS pharyngitis.

    The function supplies reference regimens only. Local guidance, allergy
    history, renal/hepatic considerations, drug interactions, pregnancy, and
    patient-specific factors remain outside the scope of this calculator.
    """
    if age_years is not None:
        age_years = _require_finite(age_years, "Age")
        if age_years < 0:
            raise ValueError("Age cannot be negative")
    if weight_kg is not None:
        weight_kg = _require_finite(weight_kg, "Weight")
        if weight_kg <= 0:
            raise ValueError("Weight must be greater than 0 kg")

    if severe_allergy:
        penicillin_allergic = True

    if not penicillin_allergic:
        if age_years is not None and age_years < 18:
            penicillin_v = "250 mg orally twice or three times daily"
            amoxicillin = (
                "50 mg/kg orally once daily (max 1000 mg), or 25 mg/kg "
                "twice daily (max 500 mg/dose)"
            )
        else:
            penicillin_v = "500 mg orally twice daily, or 250 mg four times daily"
            amoxicillin = "1000 mg orally once daily, or 500 mg twice daily"

        if weight_kg is None:
            benzathine = "600,000 units IM if <27 kg; 1,200,000 units IM if ≥27 kg"
        elif weight_kg < 27:
            benzathine = "600,000 units IM once"
        else:
            benzathine = "1,200,000 units IM once"

        return [
            {
                "drug": "Penicillin V",
                "dosage": penicillin_v,
                "duration": "10 days",
                "notes": "First-line option for confirmed GAS pharyngitis.",
            },
            {
                "drug": "Amoxicillin",
                "dosage": amoxicillin,
                "duration": "10 days",
                "notes": "First-line alternative for confirmed GAS pharyngitis.",
            },
            {
                "drug": "Benzathine penicillin G",
                "dosage": benzathine,
                "duration": "Single dose",
                "notes": "Intramuscular alternative when appropriate.",
            },
        ]

    if severe_allergy:
        return [
            {
                "drug": "Azithromycin",
                "dosage": (
                    "12 mg/kg orally once (max 500 mg), then 6 mg/kg once daily "
                    "(max 250 mg) for the next 4 days"
                ),
                "duration": "5 days",
                "notes": "Macrolide resistance varies geographically and temporally.",
            },
            {
                "drug": "Clarithromycin",
                "dosage": "7.5 mg/kg/dose orally twice daily (max 250 mg/dose)",
                "duration": "10 days",
                "notes": "Macrolide resistance varies geographically and temporally.",
            },
            {
                "drug": "Clindamycin",
                "dosage": "7 mg/kg/dose orally three times daily (max 300 mg/dose)",
                "duration": "10 days",
                "notes": "Resistance varies geographically and temporally.",
            },
        ]

    return [
        {
            "drug": "Cephalexin",
            "dosage": "20 mg/kg/dose orally twice daily (max 500 mg/dose)",
            "duration": "10 days",
            "notes": "Avoid in immediate-type hypersensitivity to penicillin.",
        },
        {
            "drug": "Cefadroxil",
            "dosage": "30 mg/kg orally once daily (max 1 g)",
            "duration": "10 days",
            "notes": "Avoid in immediate-type hypersensitivity to penicillin.",
        },
        {
            "drug": "Azithromycin",
            "dosage": (
                "12 mg/kg orally once (max 500 mg), then 6 mg/kg once daily "
                "(max 250 mg) for the next 4 days"
            ),
            "duration": "5 days",
            "notes": "Macrolide resistance varies geographically and temporally.",
        },
        {
            "drug": "Clarithromycin",
            "dosage": "7.5 mg/kg/dose orally twice daily (max 250 mg/dose)",
            "duration": "10 days",
            "notes": "Macrolide resistance varies geographically and temporally.",
        },
        {
            "drug": "Clindamycin",
            "dosage": "7 mg/kg/dose orally three times daily (max 300 mg/dose)",
            "duration": "10 days",
            "notes": "Resistance varies geographically and temporally.",
        },
    ]


def evaluate_mcisaac(
    absence_of_cough: bool = False,
    tender_anterior_cervical_nodes: bool = False,
    tonsillar_exudate_or_swelling: bool = False,
    history_of_fever_or_temp_gt_38: bool = False,
    age_years: float = 25.0,
    temperature_c: Optional[float] = None,
    penicillin_allergic: bool = False,
    severe_allergy: bool = False,
    weight_kg: Optional[float] = None,
    gas_test_result: Optional[str] = None,
    clear_viral_features: bool = False,
    high_risk_context: bool = False,
) -> McIsaacResult:
    """Evaluate the Modified Centor score and return testing-oriented guidance."""
    age_years = _require_finite(age_years, "Age")
    if age_years < 0:
        raise ValueError("Age cannot be negative")
    if temperature_c is not None:
        temperature_c = _require_finite(temperature_c, "Temperature")
    if weight_kg is not None:
        weight_kg = _require_finite(weight_kg, "Weight")
        if weight_kg <= 0:
            raise ValueError("Weight must be greater than 0 kg")

    normalized_test = _normalize_test_result(gas_test_result)
    fever_flag = bool(history_of_fever_or_temp_gt_38)
    if temperature_c is not None and temperature_c >= 38.0:
        fever_flag = True

    centor_score = calculate_raw_centor(
        absence_of_cough=absence_of_cough,
        tender_anterior_cervical_nodes=tender_anterior_cervical_nodes,
        tonsillar_exudate_or_swelling=tonsillar_exudate_or_swelling,
        history_of_fever_or_temp_gt_38=fever_flag,
    )
    age_modifier, age_warning = get_age_modifier(age_years)
    mcisaac_score = centor_score + age_modifier
    strep_pct, risk_num, risk_tier = _probability_for_score(mcisaac_score)

    warnings: List[str] = []
    if age_warning:
        warnings.append(age_warning)
    warnings.append(
        "The displayed GAS percentage is an observed prevalence estimate from the "
        "Fine et al. 2012 validation cohort; it is not an individualized probability."
    )

    score_applicable = age_years >= 3
    action = ClinicalAction.NO_TEST_NO_ABX

    if normalized_test == "positive":
        guidance = (
            "GAS has been confirmed by diagnostic testing. Antibiotic treatment is "
            "recommended; use patient-specific prescribing guidance and local policy."
        )
    elif normalized_test == "negative_radt":
        if 3 <= age_years < 18:
            guidance = (
                "RADT is negative. In symptomatic children and adolescents, obtain a "
                "back-up throat culture and treat only if confirmatory testing is positive."
            )
        else:
            guidance = (
                "RADT is negative. Routine back-up throat culture is generally not indicated "
                "in adults; reassess if the clinical course or differential diagnosis warrants it."
            )
    elif normalized_test in {"negative_culture", "negative_naat"}:
        guidance = (
            "Diagnostic testing is negative for GAS. Antibiotics for GAS pharyngitis are "
            "not indicated; consider alternative causes and symptomatic care."
        )
    elif clear_viral_features:
        guidance = (
            "Clear viral features are present. GAS testing is usually unnecessary when the "
            "clinical picture is consistent with viral pharyngitis."
        )
    elif not score_applicable:
        guidance = (
            "The McIsaac score is not applicable below age 3. Use clinical assessment and "
            "age-appropriate guidance rather than this score to decide on testing."
        )
    elif high_risk_context:
        action = ClinicalAction.TEST_RADT_OR_CULTURE
        guidance = (
            "A high-risk context is present. Consider GAS diagnostic testing even if the "
            "clinical score is low."
        )
    elif mcisaac_score <= 1:
        guidance = (
            "Low McIsaac score. Diagnostic testing is often unlikely to be helpful in an "
            "otherwise low-risk patient; apply local guidance and clinical judgment."
        )
    else:
        action = ClinicalAction.TEST_RADT_OR_CULTURE
        guidance = (
            "Consider GAS diagnostic testing (for example RADT, molecular testing, and/or "
            "throat culture according to local practice). Do not prescribe antibiotics from "
            "the clinical score alone."
        )

    antibiotic_options: List[Dict[str, str]] = []
    if normalized_test == "positive":
        antibiotic_options = get_antibiotic_regimens(
            penicillin_allergic=penicillin_allergic,
            severe_allergy=severe_allergy,
            age_years=age_years,
            weight_kg=weight_kg,
        )

    symptomatic = [
        "Use appropriate analgesia/antipyretics and maintain hydration as clinically appropriate.",
        "Reassess urgently for airway compromise, drooling, inability to swallow, severe systemic illness, or suspected deep-neck infection.",
    ]

    breakdown = {
        "absence_of_cough": bool(absence_of_cough),
        "tender_anterior_cervical_nodes": bool(tender_anterior_cervical_nodes),
        "tonsillar_exudate_or_swelling": bool(tonsillar_exudate_or_swelling),
        "history_of_fever_or_temp_gt_38": fever_flag,
        "raw_centor_score": centor_score,
        "age_years": age_years,
        "age_modifier": age_modifier,
        "final_mcisaac_score": mcisaac_score,
        "clear_viral_features": bool(clear_viral_features),
        "high_risk_context": bool(high_risk_context),
    }

    return McIsaacResult(
        centor_score=centor_score,
        age_years=age_years,
        age_modifier=age_modifier,
        mcisaac_score=mcisaac_score,
        strep_probability_pct=strep_pct,
        risk_numeric=risk_num,
        risk_tier=risk_tier,
        recommended_action=action,
        clinical_guidance=guidance,
        score_applicable=score_applicable,
        gas_test_result=normalized_test,
        antibiotic_options=antibiotic_options,
        symptomatic_measures=symptomatic,
        warnings=warnings,
        criteria_breakdown=breakdown,
    )


_TRUE_VALUES = {"1", "true", "yes", "y", "t", "pos", "positive"}
_FALSE_VALUES = {"0", "false", "no", "n", "f", "neg", "negative"}


def _read_bool(present: Dict[str, Any], aliases: List[str], default: bool = False) -> bool:
    for key in aliases:
        if key not in present or present[key] is None or str(present[key]).strip() == "":
            continue
        value = present[key]
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if value in (0, 1):
                return bool(value)
            raise ValueError(f"{key} must be a boolean or 0/1, got {value!r}")
        normalized = str(value).strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
        raise ValueError(f"{key} has an unrecognized boolean value: {value!r}")
    return default


def _read_float(
    present: Dict[str, Any], aliases: List[str], *, required: bool = False
) -> Optional[float]:
    for key in aliases:
        if key not in present or present[key] is None or str(present[key]).strip() == "":
            continue
        try:
            value = float(present[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key} must be numeric, got {present[key]!r}") from exc
        return _require_finite(value, key)
    if required:
        raise ValueError(f"Missing required field; expected one of: {', '.join(aliases)}")
    return None


def calculate_score(present: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a dictionary/CSV-like record with strict input validation."""
    no_cough = _read_bool(present, ["absence_of_cough", "no_cough", "cough_absent", "no_cough_or_coryza"])
    tender_nodes = _read_bool(present, ["tender_anterior_cervical_nodes", "tender_cervical_nodes", "lymphadenopathy", "tender_nodes", "nodes"])
    exudate = _read_bool(present, ["tonsillar_exudate_or_swelling", "tonsillar_exudate", "exudate", "pus", "tonsil_swelling", "exudates"])
    fever = _read_bool(present, ["history_of_fever_or_temp_gt_38", "history_of_fever", "fever", "fever_history", "temp_gt_38"])
    clear_viral = _read_bool(present, ["clear_viral_features", "viral_features"])
    high_risk = _read_bool(present, ["high_risk_context", "high_risk"])

    temp = _read_float(present, ["temperature_c", "temperature", "temp", "temp_c"])
    age = _read_float(present, ["age", "age_years", "patient_age"], required=True)
    weight = _read_float(present, ["weight_kg", "weight", "wt"])

    pen_allergic = _read_bool(present, ["penicillin_allergic", "penicillin_allergy", "pen_allergy", "allergic_to_penicillin"])
    severe_allergy = _read_bool(present, ["severe_allergy", "severe_penicillin_allergy", "anaphylaxis"])
    gas_result = None
    for key in ("gas_test_result", "test_result"):
        if key in present and present[key] is not None and str(present[key]).strip():
            gas_result = str(present[key])
            break

    result = evaluate_mcisaac(
        absence_of_cough=no_cough,
        tender_anterior_cervical_nodes=tender_nodes,
        tonsillar_exudate_or_swelling=exudate,
        history_of_fever_or_temp_gt_38=fever,
        age_years=float(age),
        temperature_c=temp,
        penicillin_allergic=pen_allergic,
        severe_allergy=severe_allergy,
        weight_kg=weight,
        gas_test_result=gas_result,
        clear_viral_features=clear_viral,
        high_risk_context=high_risk,
    )

    detail: Dict[str, int] = {}
    if no_cough:
        detail["Absence of cough"] = 1
    if tender_nodes:
        detail["Tender anterior cervical nodes"] = 1
    if exudate:
        detail["Tonsillar exudate/swelling"] = 1
    if fever or (temp is not None and temp >= 38.0):
        detail["Fever (≥38°C/history)"] = 1
    if result.age_modifier:
        detail[f"Age modifier ({result.age_years:g} years)"] = result.age_modifier

    return {
        "score": result.mcisaac_score,
        "centor_score": result.centor_score,
        "tier": result.risk_tier.value.lower(),
        "risk_tier": result.risk_tier.value,
        "strep_probability": result.strep_probability_pct,
        "recommended_action": result.recommended_action.value,
        "clinical_guidance": result.clinical_guidance,
        "score_applicable": result.score_applicable,
        "gas_test_result": result.gas_test_result,
        "detail": detail,
        "warnings": result.warnings,
        "antibiotics": result.antibiotic_options,
    }


def assess_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return calculate_score(row)


def process_csv(inp: str, out: str) -> List[Dict[str, Any]]:
    """Batch-evaluate a CSV and write scored records."""
    with open(inp, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if not fieldnames:
        raise ValueError("Input CSV has no header row")

    results: List[Dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        try:
            scored = assess_row(row)
        except ValueError as exc:
            patient_id = row.get("patient_id") or row.get("id") or "unknown"
            raise ValueError(f"Invalid data at CSV row {index} (patient {patient_id}): {exc}") from exc

        merged = dict(row)
        merged.update(
            {
                "centor_score": scored["centor_score"],
                "mcisaac_score": scored["score"],
                "risk_tier": scored["risk_tier"],
                "strep_probability": scored["strep_probability"],
                "recommended_action": scored["recommended_action"],
                "clinical_guidance": scored["clinical_guidance"],
            }
        )
        results.append(merged)

    out_fields = list(
        dict.fromkeys(
            fieldnames
            + [
                "centor_score",
                "mcisaac_score",
                "risk_tier",
                "strep_probability",
                "recommended_action",
                "clinical_guidance",
            ]
        )
    )

    with open(out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(results)

    return results
