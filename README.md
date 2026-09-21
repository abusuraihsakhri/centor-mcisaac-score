# Centor / Modified Centor (McIsaac) Score

### [Open the Live Application →](https://abusuraihsakhri.github.io/centor-mcisaac-score/)

A compact calculator for the Centor and Modified Centor (McIsaac) clinical scores used to stratify the likelihood of group A streptococcal (GAS) pharyngitis and support decisions about diagnostic testing.

The repository includes a dependency-free browser calculator, a Python library, a command-line interface, CSV batch processing, and automated tests. The score is a decision-support aid: it does not diagnose GAS, and antibiotics should not be prescribed from the score alone.

## What it does

The calculator assigns one point for each of the four Centor findings: fever/history of fever, absence of cough, tender anterior cervical nodes, and tonsillar exudate or swelling. The McIsaac modification then adds one point for ages 3–14, adds no age point for ages 15–44, and subtracts one point at age 45 or older.

Risk percentages shown by the implementation use the large 2012 validation cohort reported by Fine, Nizet, and Mandl. Scores of -1 and 5 are normalized to 0 and 4 for those validation estimates, matching the published analysis.

Current guidance is handled conservatively:

- Clear viral features usually make GAS testing unnecessary.
- The McIsaac scoring-system recommendation is not applied to children under 3 years.
- High-risk clinical contexts can justify testing despite a low score.
- A positive diagnostic test is required before antibiotic reference regimens are displayed.
- A negative RADT in a symptomatic child or adolescent should be backed up with throat culture; routine back-up culture is generally not indicated in adults.

## Browser application

The static application is in `web/` and is designed for GitHub Pages. It uses plain HTML, CSS, and JavaScript and does not require Python, Pyodide, a backend, cookies, or third-party runtime libraries.

Inputs and results stay in the browser. The app does not transmit clinical entries to a server.

## Command line

Evaluate one case:

```bash
python cli.py eval --age 28 --fever --no-cough --nodes
```

Include a confirmed GAS result to show reference treatment regimens:

```bash
python cli.py eval --age 28 --gas-test-result positive
```

Run the guided questionnaire:

```bash
python cli.py interactive
```

Batch-process the included CSV example:

```bash
python cli.py batch -i sample.csv -o scored_mcisaac_batch.csv
```

## Testing

No runtime Python dependencies are required.

```bash
python -m compileall -q centor.py cli.py
python -m unittest discover -s tests -v
python cli.py batch -i sample.csv -o out_smoke.csv
node --check web/app.js
node --check web/calculator.mjs
node --test web/tests/*.test.mjs
```

GitHub Actions runs the Python suite on Python 3.10–3.13 and separately tests the browser scoring module with Node.js 20.

## Clinical references

- Infectious Diseases Society of America. 2025 Clinical Practice Guideline Update on Group A Streptococcal Pharyngitis: Risk Assessment Using Clinical Scoring Systems in Children and Adults. https://www.idsociety.org/practice-guideline/streptococcal-pharyngitis2/
- CDC. Clinical Guidance for Group A Streptococcal Pharyngitis. https://www.cdc.gov/group-a-strep/hcp/clinical-guidance/strep-throat.html
- Fine AM, Nizet V, Mandl KD. Large-Scale Validation of the Centor and McIsaac Scores to Predict Group A Streptococcal Pharyngitis. *Arch Intern Med.* 2012;172(11):847–852. doi:10.1001/archinternmed.2012.950.
- McIsaac WJ, White D, Tannenbaum D, Low DE. A clinical score to reduce unnecessary antibiotic use in patients with sore throat. *CMAJ.* 1998;158(1):75–83.

## Browser compatibility

The static app uses standard ES modules, CSS Grid, and native form controls. Current versions of Chrome/Chromium, Edge, Firefox, and Safari are supported. JavaScript must be enabled.

## License

MIT. See [LICENSE](LICENSE).
