import test from "node:test";
import assert from "node:assert/strict";
import { ageModifier, calculateScore } from "../calculator.mjs";

test("age modifiers match McIsaac criteria", () => {
  assert.equal(ageModifier(3), 1);
  assert.equal(ageModifier(14), 1);
  assert.equal(ageModifier(15), 0);
  assert.equal(ageModifier(44), 0);
  assert.equal(ageModifier(45), -1);
});

test("full pediatric criteria produce raw score 5 and normalized 55% estimate", () => {
  const result = calculateScore({ age: 8, fever: true, noCough: true, nodes: true, exudate: true, testResult: "not_tested" });
  assert.equal(result.centor, 4);
  assert.equal(result.mcisaac, 5);
  assert.equal(result.estimate.label, "55%");
  assert.equal(result.action, "Consider GAS testing");
  assert.match(result.guidance, /Do not prescribe antibiotics/);
});

test("positive test changes guidance to treatment", () => {
  const result = calculateScore({ age: 25, testResult: "positive" });
  assert.equal(result.action, "Treat confirmed GAS");
});

test("negative RADT in child requests backup culture", () => {
  const result = calculateScore({ age: 8, testResult: "negative_radt" });
  assert.equal(result.action, "Back-up throat culture");
});

test("clear viral features override score-driven testing", () => {
  const result = calculateScore({ age: 25, fever: true, noCough: true, nodes: true, exudate: true, viralFeatures: true, testResult: "not_tested" });
  assert.equal(result.action, "Usually no GAS test");
});

test("high-risk context can trigger testing at a low score", () => {
  const result = calculateScore({ age: 25, highRisk: true, testResult: "not_tested" });
  assert.equal(result.mcisaac, 0);
  assert.equal(result.action, "Consider GAS testing");
});

test("under age three is marked not applicable", () => {
  const result = calculateScore({ age: 2, noCough: true, testResult: "not_tested" });
  assert.equal(result.applicable, false);
  assert.equal(result.action, "Score not applicable");
});

test("invalid age is rejected", () => {
  assert.throws(() => calculateScore({ age: "", testResult: "not_tested" }), /Age must be a finite number/);
});
