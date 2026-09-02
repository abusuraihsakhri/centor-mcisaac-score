# Centor Mcisaac Score

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Centor and Modified Centor (McIsaac) Score for Streptococcal Pharyngitis
Implements clinical scoring criteria (Centor et al. 1981, McIsaac et al. 1998, 2004)
for Group A Beta-Hemolytic Streptococcal (GABHS) pharyngitis evaluation and diagnostic stewardship.

Author: Dr. Abu Suraih Sakhri
License: MIT

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`ClinicalAction`** — dedicated module for clinical action evaluation and state verification.
- **`RiskTier`** — dedicated module for risk tier evaluation and state verification.
- **`CentorCriteriaDetail`** — dedicated module for centor criteria detail evaluation and state verification.
- **`McIsaacResult`** — dedicated module for mc isaac result evaluation and state verification.

---

## 📐 Mathematical Formulation & Logic

```text
  score = 0
  Calculates composite McIsaac score (-1 to 5).
  centor_score = calculate_raw_centor(
  mcisaac_score = centor_score + age_mod
  elif mcisaac_score == 1:
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --- <value> --age <value> --temp <value> --temperature <value>
```

### Parameter Reference
- `---`: Specifies input measurement or parameter value.
- `--age`: Specifies input measurement or parameter value.
- `--temp`: Specifies input measurement or parameter value.
- `--temperature`: Specifies input measurement or parameter value.
- `--fever`: Specifies input measurement or parameter value.
- `--no-cough`: Specifies input measurement or parameter value.
- `--cough-absent`: Specifies input measurement or parameter value.
- `--nodes`: Specifies input measurement or parameter value.
- `--tender-nodes`: Specifies input measurement or parameter value.
- `--exudate`: Specifies input measurement or parameter value.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `patient_id` | Parameter / observation metric | Required |
| `absence_of_cough` | Parameter / observation metric | Required |
| `tender_cervical_nodes` | Parameter / observation metric | Required |
| `tonsillar_exudate` | Parameter / observation metric | Required |
| `fever` | Parameter / observation metric | Required |
| `age` | Parameter / observation metric | Required |
| `weight_kg` | Parameter / observation metric | Required |
| `penicillin_allergic` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t centor-mcisaac-score .
docker run -p 8000:8000 centor-mcisaac-score
```
