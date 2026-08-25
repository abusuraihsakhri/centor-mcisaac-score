# Centor & McIsaac (Modified Centor) Strep Pharyngitis Score

A robust, zero-dependency Python implementation of the **Centor Score** and **Modified Centor (McIsaac) Score** for Group A Beta-Hemolytic Streptococcal (GABHS / *Streptococcus pyogenes*) pharyngitis risk stratification and antimicrobial stewardship.

Implements clinical decision thresholds aligned with the **Infectious Diseases Society of America (IDSA)**, the **American Academy of Pediatrics (AAP)**, and landmark validation trials (*Centor et al. 1981*, *McIsaac et al. 1998, 2004*).

---

## Clinical Background & Diagnostic Utility

Group A Streptococcal (GAS) pharyngitis accounts for approximately 15%–30% of sore throats in pediatric patients (ages 3–14) and 5%–15% in adults. Treating viral pharyngitis with antibiotics increases healthcare costs, exposes patients to adverse drug events, and drives microbial resistance.

The **Centor Criteria** (1981) and subsequent **McIsaac modification** (1998, 2004) incorporate patient age to optimize pre-test probability estimation, enabling clinicians to avoid unnecessary Rapid Antigen Detection Tests (RADT) and throat cultures in low-risk individuals while promptly identifying candidates for testing or therapy.

---

## Scoring System & Algorithmic Rules

### 1. Centor Criteria (4 Core Factors, 1 Point Each)
1. **Absence of cough** (+1)
2. **Swollen / tender anterior cervical lymph nodes** (+1)
3. **Tonsillar exudate or tonsillar swelling** (+1)
4. **History of fever or measured temperature > 38.0 °C (100.4 °F)** (+1)

---

### 2. McIsaac Age Modifiers

| Age Group | Modifier | Rationale |
| :--- | :---: | :--- |
| **3 to 14 years** | **+1** | Peak incidence of GAS pharyngitis (~30%–40% prevalence) |
| **15 to 44 years** | **0** | Baseline adult incidence (~15% prevalence) |
| **$\ge$ 45 years** | **-1** | Lower incidence in older adults (~5% prevalence) |
| **< 3 years** | **0** | *Caveat*: GAS pharyngitis is rare; acute rheumatic fever is extraordinarily uncommon under 3 yrs. Testing is generally discouraged unless household contact. |

---

### 3. Risk Stratification & Clinical Action Thresholds

| McIsaac Score | Estimated GAS Risk | Action Threshold (IDSA / CDC / ACP) |
| :---: | :---: | :--- |
| **$\le 0$** | **1% – 2.5%** | **No testing, no antibiotics**. Provide symptomatic analgesia & supportive care. |
| **1** | **5% – 10%** | **No testing, no antibiotics**. Provide symptomatic care. |
| **2** | **11% – 17%** | **Perform RADT or throat swab culture**. Treat with antibiotics only if test is positive. |
| **3** | **28% – 35%** | **Perform RADT or culture**. Treat if positive; consider empiric antibiotics if high clinical suspicion. |
| **$\ge 4$ (4 or 5)**| **51% – 53%** | **Empiric antibiotic therapy** OR **RADT + antibiotic treatment if positive**. |

---

## Guideline Antimicrobial Regimens (IDSA / AAP)

| Clinical Presentation | Drug & Route | Dosing Regimen | Duration |
| :--- | :--- | :--- | :--- |
| **First-Line Standard** | Penicillin V Potassium (Oral) | Adult: 500 mg BD/TDS<br>Peds: 250 mg BD (<27 kg) / 500 mg BD ($\ge$27 kg) | 10 days |
| **First-Line Peds Option** | Amoxicillin (Oral suspension) | Adult: 500 mg BD or 1000 mg OD<br>Peds: 50 mg/kg once daily (max 1000 mg) | 10 days |
| **Parenteral Alternative** | Benzathine Penicillin G (IM) | 1,200,000 U single dose (600,000 U if <27 kg) | Single dose |
| **Penicillin Allergy (Non-Severe)** | Cephalexin (Oral) | Adult: 500 mg BD<br>Peds: 20 mg/kg/dose BD | 10 days |
| **Severe Penicillin Allergy** | Azithromycin (Oral) | Adult: 500 mg Day 1, 250 mg Days 2–5<br>Peds: 12 mg/kg Day 1, 6 mg/kg Days 2–5 | 5 days |
| **Lincosamide Alternative** | Clindamycin (Oral) | Adult: 300 mg TDS<br>Peds: 20 mg/kg/day in 3 divided doses | 10 days |

---

## Project Structure

```
centor-mcisaac-score/
├── centor.py               # Core computational engine and scoring rules
├── cli.py                  # Command-line interface with interactive mode
├── test_centor.py          # Unit test suite (27+ test cases)
├── benchmark_dataset.json  # Standardized clinical benchmark test cases
├── sample.csv              # Sample batch dataset
├── Dockerfile              # Container specification
├── docker-compose.yml      # Docker compose configuration
└── README.md               # Clinical documentation and usage manual
```

---

## CLI Usage

### Interactive Clinical Questionnaire
```bash
python cli.py interactive
```

### Single Case Assessment
```bash
# Evaluate a 9-year-old child with fever, no cough, tonsillar exudates, and tender lymph nodes
python cli.py eval --no-cough --nodes --exudate --fever --age 9

# JSON format output for integration
python cli.py eval --no-cough --nodes --exudate --fever --age 9 --json
```

### Batch CSV Evaluation
```bash
python cli.py batch -i sample.csv -o results.csv
```

---

## Programmatic Usage

```python
from centor import evaluate_mcisaac, ClinicalAction

res = evaluate_mcisaac(
    absence_of_cough=True,
    tender_anterior_cervical_nodes=True,
    tonsillar_exudate_or_swelling=True,
    history_of_fever_or_temp_gt_38=True,
    age_years=8.0,
    penicillin_allergic=False,
)

print(f"Raw Centor: {res.centor_score}/4")
print(f"McIsaac Score: {res.mcisaac_score}/5")
print(f"Action: {res.recommended_action.value}")
print(f"Guidance: {res.clinical_guidance}")
```

---

## Test Verification

Run all unit tests using `unittest`:
```bash
python -m unittest discover -s . -p "test_*.py" -v
```

---

## References

1. **Centor RM, et al.** (1981). *The diagnosis of strep throat in adults in the emergency room*. Med Decis Making; 1(3):239–246.
2. **McIsaac WJ, et al.** (1998). *A clinical score to reduce unnecessary antibiotic use in patients with sore throat*. CMAJ; 158(1):75–83.
3. **McIsaac WJ, et al.** (2004). *Empirical validation of guidelines for the management of pharyngitis in children and adults*. JAMA; 291(13):1587–1595.
4. **Shulman ST, et al.** (2012). *Clinical Practice Guideline for the Diagnosis and Management of Group A Streptococcal Pharyngitis: 2012 Update by the Infectious Diseases Society of America*. Clin Infect Dis; 55(10):e86–e102.

---

## License

MIT License. Developed for clinical decision support and antimicrobial stewardship research.
