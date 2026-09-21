import { calculateScore } from "./calculator.mjs";

const form = document.querySelector("#score-form");
const ageInput = document.querySelector("#age");
const tempInput = document.querySelector("#temperature");
const resultPanel = document.querySelector("#result-panel");
const scoreValue = document.querySelector("#score-value");
const centorValue = document.querySelector("#centor-value");
const ageModifierValue = document.querySelector("#age-modifier-value");
const probabilityValue = document.querySelector("#probability-value");
const riskTierValue = document.querySelector("#risk-tier-value");
const actionValue = document.querySelector("#action-value");
const guidanceValue = document.querySelector("#guidance-value");
const criteriaValue = document.querySelector("#criteria-value");
const notesValue = document.querySelector("#notes-value");
const errorBox = document.querySelector("#form-error");
const themeButton = document.querySelector("#theme-toggle");
const themeText = document.querySelector("#theme-text");

function currentInput() {
  return {
    age: ageInput.value,
    temperature: tempInput.value,
    fever: document.querySelector("#fever").checked,
    noCough: document.querySelector("#no-cough").checked,
    nodes: document.querySelector("#nodes").checked,
    exudate: document.querySelector("#exudate").checked,
    viralFeatures: document.querySelector("#viral-features").checked,
    highRisk: document.querySelector("#high-risk").checked,
    testResult: document.querySelector("#test-result").value,
  };
}

function signed(value) {
  return value > 0 ? `+${value}` : String(value);
}

function render(result) {
  errorBox.hidden = true;
  scoreValue.textContent = String(result.mcisaac);
  centorValue.textContent = `${result.centor} / 4`;
  ageModifierValue.textContent = signed(result.modifier);
  probabilityValue.textContent = result.estimate.detail;
  riskTierValue.textContent = result.estimate.tier;
  actionValue.textContent = result.action;
  guidanceValue.textContent = result.guidance;

  criteriaValue.replaceChildren();
  Object.entries(result.criteria).forEach(([name, present]) => {
    const item = document.createElement("li");
    item.className = present ? "criterion criterion--met" : "criterion";
    item.textContent = `${present ? "+1" : "0"} · ${name}`;
    criteriaValue.appendChild(item);
  });
  if (result.modifier !== 0) {
    const item = document.createElement("li");
    item.className = "criterion criterion--age";
    item.textContent = `${signed(result.modifier)} · Age modifier`;
    criteriaValue.appendChild(item);
  }

  notesValue.replaceChildren();
  result.notes.forEach((note) => {
    const item = document.createElement("li");
    item.textContent = note;
    notesValue.appendChild(item);
  });

  resultPanel.dataset.tier = String(result.normalized);
  resultPanel.focus({ preventScroll: true });
}

function runCalculation(event) {
  event?.preventDefault();
  try {
    render(calculateScore(currentInput()));
  } catch (error) {
    errorBox.textContent = error instanceof Error ? error.message : "Unable to calculate the score.";
    errorBox.hidden = false;
    ageInput.focus();
  }
}

function resetForm() {
  form.reset();
  ageInput.value = "25";
  tempInput.value = "";
  runCalculation();
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("centor-theme", theme);
  const dark = theme === "dark";
  themeButton.setAttribute("aria-pressed", String(dark));
  themeText.textContent = dark ? "Light" : "Dark";
}

function initTheme() {
  const saved = localStorage.getItem("centor-theme");
  const preferred = window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  setTheme(saved || preferred);
}

form.addEventListener("submit", runCalculation);
document.querySelector("#reset-button").addEventListener("click", resetForm);
themeButton.addEventListener("click", () => {
  setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
});

document.querySelectorAll("input[type='checkbox'], select").forEach((control) => {
  control.addEventListener("change", () => {
    if (ageInput.value !== "") runCalculation();
  });
});

initTheme();
runCalculation();
