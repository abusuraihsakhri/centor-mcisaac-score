# Centor & Modified Centor (McIsaac) Pharyngitis Risk Calculator

> **Domain:** Primary Care, Emergency Medicine & Infectious Disease  
> **Clinical Guidelines:** Centor et al. (Med Decis Making 1981), McIsaac et al. (CMAJ 1998, JAMA 2004), IDSA Clinical Practice Guideline for Group A Streptococcal Pharyngitis (2012)

---

## 📖 Clinical Overview

The **Centor and Modified Centor (McIsaac) Strep Score Calculator** provides standardized risk stratification for Group A Beta-Hemolytic Streptococcal (GABHS / *Streptococcus pyogenes*) pharyngitis in pediatric and adult patients presenting with acute sore throat.

By systematically synthesizing key clinical criteria (tonsillar exudates, tender anterior cervical adenopathy, fever history, cough absence, and age stratification), the calculator prevents unnecessary antibiotic overprescription while identifying patients who require Rapid Antigen Detection Testing (RADT), throat culture, or immediate empiric therapy.

### Scoring Criteria

| Clinical Feature | Description | Points |
|:---|:---|:---|
| **Absence of cough** | Patient does not report active cough | +1 |
| **Swollen / tender cervical nodes** | Tender anterior cervical lymphadenopathy | +1 |
| **Tonsillar exudates or swelling** | Tonsillar enlargement or white exudate | +1 |
| **History of fever / temp > 38.0°C** | Objective or subjective acute febrile episode | +1 |
| **Age 3 to 14 years** | Pediatric age window with peak incidence | +1 |
| **Age 15 to 44 years** | Baseline adolescent/adult incidence | 0 |
| **Age $\ge 45$ years** | Lower GABHS incidence in older adults | -1 |

### Risk Tiers & Clinical Actions

| McIsaac Score | Risk Tier | GABHS Probability | Management Recommendation |
|:---|:---|:---|:---|
| **$\le 0$** | Very Low | 1% – 2.5% | No throat swab or culture; no antibiotics. Symptomatic analgesia. |
| **1** | Low | 5% – 10% | No testing or antibiotics indicated. Supportive care. |
| **2** | Intermediate | 11% – 17% | Perform RADT or throat culture; treat only if positive. |
| **3** | High | 28% – 35% | Perform RADT/culture; treat if positive or empiric based on severity. |
| **$\ge 4$** | Very High | 51% – 53% | Empiric antibiotic therapy or rapid testing with treatment indicated. |

---

## 💻 CLI Quickstart & Usage

### 1. Evaluate Individual Patient Case
```bash
python cli.py eval --fever --exudate --nodes --no-cough --age 8 --weight 25
```

### 2. Interactive Guided Questionnaire
```bash
python cli.py interactive
```

### 3. Batch Process Patient Cohort
```bash
python cli.py batch -i sample.csv -o out_results.csv
```

---

## 🧪 Verification & Testing

Execute comprehensive unit tests via pytest:
```bash
python -m pytest -p no:zarr
```
