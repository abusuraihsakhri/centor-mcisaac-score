export const VALIDATION_ESTIMATES = Object.freeze({
  0: { label: "8%", detail: "8% (95% CI 8–9%)", tier: "Very low" },
  1: { label: "14%", detail: "14% (95% CI 13–14%)", tier: "Low" },
  2: { label: "23%", detail: "23% (95% CI 23–23%)", tier: "Intermediate" },
  3: { label: "37%", detail: "37% (95% CI 37–37%)", tier: "High" },
  4: { label: "55%", detail: "55% (95% CI 55–56%)", tier: "Very high" },
});

const TEST_RESULTS = new Set(["not_tested", "positive", "negative_radt", "negative_culture", "negative_naat"]);

function finiteNumber(value, name) {
  if (value === "" || value === null || value === undefined) {
    throw new Error(`${name} must be a finite number.`);
  }
  const number = Number(value);
  if (!Number.isFinite(number)) throw new Error(`${name} must be a finite number.`);
  return number;
}

export function ageModifier(age) {
  const value = finiteNumber(age, "Age");
  if (value < 0) throw new Error("Age cannot be negative.");
  if (value < 3) return 0;
  if (value <= 14) return 1;
  if (value <= 44) return 0;
  return -1;
}

export function calculateScore(input) {
  const age = finiteNumber(input.age, "Age");
  if (age < 0) throw new Error("Age cannot be negative.");

  const testResult = input.testResult || "not_tested";
  if (!TEST_RESULTS.has(testResult)) throw new Error("Unrecognized GAS test result.");

  const fever = Boolean(input.fever) || (input.temperature !== "" && input.temperature != null && finiteNumber(input.temperature, "Temperature") >= 38);
  const criteria = {
    "Absence of cough": Boolean(input.noCough),
    "Tender anterior cervical nodes": Boolean(input.nodes),
    "Tonsillar exudate or swelling": Boolean(input.exudate),
    "Fever ≥38°C or fever history": fever,
  };

  const centor = Object.values(criteria).filter(Boolean).length;
  const modifier = ageModifier(age);
  const mcisaac = centor + modifier;
  const normalized = Math.min(4, Math.max(0, mcisaac));
  const estimate = VALIDATION_ESTIMATES[normalized];
  const applicable = age >= 3;

  let action = "No score-based treatment";
  let guidance;

  if (testResult === "positive") {
    action = "Treat confirmed GAS";
    guidance = "GAS is confirmed. Antibiotic treatment is recommended; use patient-specific prescribing guidance and local policy.";
  } else if (testResult === "negative_radt") {
    action = age >= 3 && age < 18 ? "Back-up throat culture" : "No routine back-up culture";
    guidance = age >= 3 && age < 18
      ? "The RADT is negative. In symptomatic children and adolescents, obtain a back-up throat culture and treat only if confirmatory testing is positive."
      : "The RADT is negative. Routine back-up throat culture is generally not indicated in adults; reassess if the course or differential diagnosis warrants it.";
  } else if (testResult === "negative_culture" || testResult === "negative_naat") {
    action = "No GAS antibiotics";
    guidance = "Diagnostic testing is negative for GAS. Consider alternative causes and symptomatic care.";
  } else if (input.viralFeatures) {
    action = "Usually no GAS test";
    guidance = "Clear viral features are present. GAS testing is usually unnecessary when the clinical picture is consistent with viral pharyngitis.";
  } else if (!applicable) {
    action = "Score not applicable";
    guidance = "The McIsaac score is not intended for children under 3 years. Use age-appropriate clinical guidance rather than this score to decide on testing.";
  } else if (input.highRisk) {
    action = "Consider GAS testing";
    guidance = "A high-risk context is present. Consider GAS diagnostic testing even if the clinical score is low.";
  } else if (mcisaac <= 1) {
    action = "Testing often unnecessary";
    guidance = "Low McIsaac score. Diagnostic testing is often unlikely to be helpful in an otherwise low-risk patient; apply local guidance and clinical judgment.";
  } else {
    action = "Consider GAS testing";
    guidance = "Consider GAS diagnostic testing according to local practice. Do not prescribe antibiotics from the clinical score alone.";
  }

  const notes = [
    "The percentage shown is observed GAS test positivity in the Fine et al. 2012 validation cohort, not an individualized diagnostic probability.",
  ];
  if (age < 3) notes.unshift("The 2025 IDSA scoring-system recommendation does not apply to children under 3 years.");
  if (input.highRisk) notes.push("High-risk contexts can warrant testing despite a low score.");

  return {
    age,
    centor,
    modifier,
    mcisaac,
    normalized,
    estimate,
    applicable,
    action,
    guidance,
    notes,
    criteria,
    testResult,
  };
}
