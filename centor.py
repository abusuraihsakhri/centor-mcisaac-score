"""
Centor and Modified Centor (McIsaac) Score for Streptococcal Pharyngitis
Implements clinical scoring criteria (Centor et al. 1981, McIsaac et al. 1998, 2004)
for Group A Beta-Hemolytic Streptococcal (GABHS) pharyngitis evaluation and diagnostic stewardship.

Author: Dr. Abu Suraih Sakhri
License: MIT
"""

from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class ClinicalAction(str, Enum):
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
    antibiotic_options: List[Dict[str, str]] = field(default_factory=list)
    symptomatic_measures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    criteria_breakdown: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["risk_tier"] = self.risk_tier.value
        d["recommended_action"] = self.recommended_action.value
        return d


def calculate_raw_centor(
    absence_of_cough: bool = False,
    tender_anterior_cervical_nodes: bool = False,
    tonsillar_exudate_or_swelling: bool = False,
    history_of_fever_or_temp_gt_38: bool = False,
) -> int:
    """
    Computes original 4-point Centor criteria (0 to 4).
    Each present criterion scores +1.
    """
    score = 0
    if bool(absence_of_cough):
        score += 1
    if bool(tender_anterior_cervical_nodes):
        score += 1
    if bool(tonsillar_exudate_or_swelling):
        score += 1
    if bool(history_of_fever_or_temp_gt_38):
        score += 1
    return score


def get_age_modifier(age_years: float) -> Tuple[int, Optional[str]]:
    """
    Computes McIsaac age modifier:
      - Age 3 to 14: +1
      - Age 15 to 44: 0
      - Age >= 45: -1
      - Age < 3: 0 with clinical caveat (GAS rare under 3 years)
    """
    if age_years < 0:
        raise ValueError(f"Age cannot be negative: {age_years}")

    warning = None
    if age_years < 3.0:
        modifier = 0
        warning = "CAUTION: GAS pharyngitis is rare in children < 3 years old. Testing and scoring are generally not indicated unless special risk factors exist."
    elif 3.0 <= age_years <= 14.0:
        modifier = 1
    elif 15.0 <= age_years <= 44.0:
        modifier = 0
    else:  # age >= 45
        modifier = -1

    return modifier, warning


def calculate_mcisaac_score(centor_score: int, age_years: float) -> int:
    """
    Calculates composite McIsaac score (-1 to 5).
    """
    if not (0 <= centor_score <= 4):
        raise ValueError(f"Centor score must be between 0 and 4, got: {centor_score}")
    mod, _ = get_age_modifier(age_years)
    return centor_score + mod


def get_antibiotic_regimens(
    penicillin_allergic: bool = False,
    severe_allergy: bool = False,
    age_years: Optional[float] = None,
    weight_kg: Optional[float] = None,
) -> List[Dict[str, str]]:
    """
    Returns IDSA/AAP/CDC recommended treatment regimens for confirmed/empiric GAS pharyngitis.
    """
    regimens = []
    if not penicillin_allergic:
        if age_years is not None and age_years < 12:
            dose_peds = f"{min(500, round(weight_kg * 12.5))} mg" if weight_kg else "250 mg (<27 kg) or 500 mg (>=27 kg)"
            regimens.append({
                "drug": "Penicillin V potassium (Oral)",
                "dosage": f"{dose_peds} 2 to 3 times daily",
                "duration": "10 days",
                "preference": "First-line preferred",
                "notes": "Drug of choice for narrow spectrum and proven efficacy in acute rheumatic fever prevention."
            })
            regimens.append({
                "drug": "Amoxicillin (Oral suspension)",
                "dosage": f"{min(1000, round(weight_kg * 50))} mg/day divided once or twice daily (max 1000 mg/day)" if weight_kg else "50 mg/kg once daily (max 1000 mg)",
                "duration": "10 days",
                "preference": "First-line alternative in young children",
                "notes": "Often preferred in pediatrics due to superior taste and palatability."
            })
        else:
            regimens.append({
                "drug": "Penicillin V potassium (Oral)",
                "dosage": "500 mg 2 to 3 times daily (or 250 mg 4 times daily)",
                "duration": "10 days",
                "preference": "First-line drug of choice",
                "notes": "Standard regimen for eradication and preventing non-suppurative complications."
            })
            regimens.append({
                "drug": "Amoxicillin (Oral)",
                "dosage": "500 mg twice daily OR 1000 mg once daily",
                "duration": "10 days",
                "preference": "First-line alternative",
                "notes": "Ensure patient has no infectious mononucleosis (rash risk)."
            })
        regimens.append({
            "drug": "Benzathine Penicillin G (Intramuscular)",
            "dosage": "1,200,000 units IM single dose (600,000 units if < 27 kg)",
            "duration": "Single dose",
            "preference": "Parenteral alternative",
            "notes": "Ideal if oral adherence or GI absorption is questionable."
        })
    else:
        if severe_allergy:
            # Type 1 IgE-mediated (anaphylaxis/angioedema)
            regimens.append({
                "drug": "Azithromycin (Oral)",
                "dosage": "12 mg/kg once daily (max 500 mg) on Day 1, then 6 mg/kg once daily (max 250 mg) Days 2-5 (or 500 mg Day 1, 250 mg Days 2-5 for adults)",
                "duration": "5 days",
                "preference": "Preferred macrolide for severe penicillin allergy",
                "notes": "Check regional macrolide resistance rates. Monitor QT interval if indicated."
            })
            regimens.append({
                "drug": "Clarithromycin (Oral)",
                "dosage": "250 mg twice daily (Pediatric: 15 mg/kg/day divided BD)",
                "duration": "10 days",
                "preference": "Alternative macrolide",
                "notes": "Take with meals to reduce GI irritation."
            })
            regimens.append({
                "drug": "Clindamycin (Oral)",
                "dosage": "300 mg three times daily (Pediatric: 20 mg/kg/day divided TDS)",
                "duration": "10 days",
                "preference": "Lincosamide alternative",
                "notes": "Effective for recurrent or macrolide-resistant GABHS."
            })
        else:
            # Non-severe allergy (minor rash)
            regimens.append({
                "drug": "Cephalexin (Cefalexin)",
                "dosage": "500 mg twice daily (Pediatric: 20 mg/kg/dose twice daily)",
                "duration": "10 days",
                "preference": "First-generation cephalosporin for non-severe allergy",
                "notes": "Safe in non-IgE mediated penicillin reactions."
            })
            regimens.append({
                "drug": "Cefadroxil",
                "dosage": "1000 mg once daily (Pediatric: 30 mg/kg once daily)",
                "duration": "10 days",
                "preference": "Alternative cephalosporin",
                "notes": "Once-daily dosing facilitates compliance."
            })
            regimens.append({
                "drug": "Azithromycin (Oral)",
                "dosage": "500 mg Day 1, then 250 mg Days 2-5",
                "duration": "5 days",
                "preference": "Macrolide alternative",
                "notes": "Use if cephalosporin allergy is also suspected."
            })

    return regimens


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
) -> McIsaacResult:
    """
    Comprehensive evaluation of Modified Centor (McIsaac) score.
    """
    # Auto-detect fever if temperature is provided
    fever_flag = history_of_fever_or_temp_gt_38
    if temperature_c is not None:
        if temperature_c >= 38.0:
            fever_flag = True

    centor_score = calculate_raw_centor(
        absence_of_cough=absence_of_cough,
        tender_anterior_cervical_nodes=tender_anterior_cervical_nodes,
        tonsillar_exudate_or_swelling=tonsillar_exudate_or_swelling,
        history_of_fever_or_temp_gt_38=fever_flag,
    )

    age_mod, warning_msg = get_age_modifier(age_years)
    mcisaac_score = centor_score + age_mod

    warnings = []
    if warning_msg:
        warnings.append(warning_msg)

    # Risk mapping and action thresholds (IDSA / McIsaac)
    if mcisaac_score <= 0:
        strep_pct = "1% - 2.5%"
        risk_num = 1.8
        risk_tier = RiskTier.VERY_LOW
        action = ClinicalAction.NO_TEST_NO_ABX
        guidance = "Very low risk of Group A Strep (1-2.5%). No diagnostic testing (throat swab/RADT) or antibiotic treatment indicated. Provide symptomatic care."
    elif mcisaac_score == 1:
        strep_pct = "5% - 10%"
        risk_num = 7.5
        risk_tier = RiskTier.LOW
        action = ClinicalAction.NO_TEST_NO_ABX
        guidance = "Low risk of Group A Strep (5-10%). Routine throat swab and antibiotics not recommended. Manage with analgesia and supportive care."
    elif mcisaac_score == 2:
        strep_pct = "11% - 17%"
        risk_num = 14.0
        risk_tier = RiskTier.INTERMEDIATE
        action = ClinicalAction.TEST_RADT_OR_CULTURE
        guidance = "Intermediate risk of Group A Strep (11-17%). Perform Rapid Antigen Detection Test (RADT) or throat culture. Treat with antibiotics only if test is positive."
    elif mcisaac_score == 3:
        strep_pct = "28% - 35%"
        risk_num = 31.5
        risk_tier = RiskTier.HIGH
        action = ClinicalAction.TEST_RADT_OR_CULTURE
        guidance = "Elevated risk of Group A Strep (28-35%). Perform RADT or throat culture. Treat if positive, or initiate empiric therapy if clinical context / local prevalence is high."
    else:  # score >= 4
        strep_pct = "51% - 53%"
        risk_num = 52.0
        risk_tier = RiskTier.VERY_HIGH
        action = ClinicalAction.EMPIRIC_ABX_OR_TEST
        guidance = "High probability of Group A Strep (>50%). Empiric antibiotic therapy or rapid testing with treatment is strongly indicated."

    abx_list = []
    if action in (ClinicalAction.TEST_RADT_OR_CULTURE, ClinicalAction.EMPIRIC_ABX_OR_TEST):
        abx_list = get_antibiotic_regimens(
            penicillin_allergic=penicillin_allergic,
            severe_allergy=severe_allergy,
            age_years=age_years,
            weight_kg=weight_kg,
        )

    symptomatic = [
        "Analgesia: Paracetamol / Acetaminophen (10-15 mg/kg in children, 500-1000 mg in adults) or Ibuprofen (10 mg/kg in children, 400 mg in adults) for throat pain and fever.",
        "Warm salt-water gargles (for cooperative children >= 6 years and adults).",
        "Adequate fluid intake (warm teas with honey or cool soothing liquids).",
        "Lozenges or throat sprays containing local anesthetic / anti-inflammatory agents.",
        "Safety netting: Instruct patient/caregivers to return immediately if worsening swallowing, difficulty breathing, drooling, or high persistent fevers develop.",
    ]

    breakdown = {
        "absence_of_cough": absence_of_cough,
        "tender_anterior_cervical_nodes": tender_anterior_cervical_nodes,
        "tonsillar_exudate_or_swelling": tonsillar_exudate_or_swelling,
        "history_of_fever_or_temp_gt_38": fever_flag,
        "raw_centor_score": centor_score,
        "age_years": age_years,
        "age_modifier": age_mod,
        "final_mcisaac_score": mcisaac_score,
    }

    return McIsaacResult(
        centor_score=centor_score,
        age_years=age_years,
        age_modifier=age_mod,
        mcisaac_score=mcisaac_score,
        strep_probability_pct=strep_pct,
        risk_numeric=risk_num,
        risk_tier=risk_tier,
        recommended_action=action,
        clinical_guidance=guidance,
        antibiotic_options=abx_list,
        symptomatic_measures=symptomatic,
        warnings=warnings,
        criteria_breakdown=breakdown,
    )


def calculate_score(present: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standard interface accepting dictionary/row parameters.
    Maps various column names and types cleanly.
    """
    def _bool(key_aliases: List[str]) -> bool:
        for k in key_aliases:
            if k in present:
                v = present[k]
                if isinstance(v, bool):
                    return v
                if isinstance(v, (int, float)):
                    return v > 0
                if isinstance(v, str):
                    return v.strip().lower() in ("1", "true", "yes", "y", "t", "pos", "positive")
        return False

    def _float(key_aliases: List[str], default: float) -> float:
        for k in key_aliases:
            if k in present and present[k] is not None and str(present[k]).strip() != "":
                try:
                    return float(present[k])
                except (ValueError, TypeError):
                    pass
        return default

    no_cough = _bool(["absence_of_cough", "no_cough", "cough_absent", "no_cough_or_coryza"])
    tender_nodes = _bool(["tender_anterior_cervical_nodes", "tender_cervical_nodes", "lymphadenopathy", "tender_nodes", "nodes"])
    exudate = _bool(["tonsillar_exudate_or_swelling", "tonsillar_exudate", "exudate", "pus", "tonsil_swelling", "exudates"])
    fever = _bool(["history_of_fever_or_temp_gt_38", "history_of_fever", "fever", "fever_history", "temp_gt_38"])

    temp = None
    if any(k in present for k in ("temperature_c", "temperature", "temp", "temp_c")):
        temp = _float(["temperature_c", "temperature", "temp", "temp_c"], 37.0)

    age = _float(["age", "age_years", "patient_age"], 30.0)
    weight = None
    if any(k in present for k in ("weight_kg", "weight", "wt")):
        weight = _float(["weight_kg", "weight", "wt"], 70.0)

    pen_allergic = _bool(["penicillin_allergic", "penicillin_allergy", "pen_allergy", "allergic_to_penicillin"])
    severe_allergy = _bool(["severe_allergy", "severe_penicillin_allergy", "anaphylaxis"])

    res = evaluate_mcisaac(
        absence_of_cough=no_cough,
        tender_anterior_cervical_nodes=tender_nodes,
        tonsillar_exudate_or_swelling=exudate,
        history_of_fever_or_temp_gt_38=fever,
        age_years=age,
        temperature_c=temp,
        penicillin_allergic=pen_allergic,
        severe_allergy=severe_allergy,
        weight_kg=weight,
    )

    detail_dict = {}
    if no_cough: detail_dict["Absence of cough"] = 1
    if tender_nodes: detail_dict["Tender anterior cervical nodes"] = 1
    if exudate: detail_dict["Tonsillar exudate/swelling"] = 1
    if fever or (temp and temp >= 38.0): detail_dict["Fever (>38C / history)"] = 1
    if res.age_modifier != 0: detail_dict[f"Age modifier ({res.age_years} yrs)"] = res.age_modifier

    return {
        "score": res.mcisaac_score,
        "centor_score": res.centor_score,
        "tier": res.risk_tier.value.lower(),
        "risk_tier": res.risk_tier.value,
        "strep_probability": res.strep_probability_pct,
        "recommended_action": res.recommended_action.value,
        "clinical_guidance": res.clinical_guidance,
        "detail": detail_dict,
        "warnings": res.warnings,
        "antibiotics": res.antibiotic_options,
    }


def assess_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return calculate_score(row)


def process_csv(inp: str, out: str) -> List[Dict[str, Any]]:
    """
    Batch evaluates a CSV file of sore throat cases and saves scored outputs.
    """
    with open(inp, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    results = []
    for r in rows:
        scored = assess_row(r)
        merged = dict(r)
        merged["centor_score"] = scored["centor_score"]
        merged["mcisaac_score"] = scored["score"]
        merged["risk_tier"] = scored["risk_tier"]
        merged["strep_probability"] = scored["strep_probability"]
        merged["recommended_action"] = scored["recommended_action"]
        merged["clinical_guidance"] = scored["clinical_guidance"]
        results.append(merged)

    out_fields = list(dict.fromkeys(fieldnames + [
        "centor_score", "mcisaac_score", "risk_tier",
        "strep_probability", "recommended_action", "clinical_guidance"
    ]))

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(results)

    return results
