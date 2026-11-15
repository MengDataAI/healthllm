# HealthLLM — The Open Health AI Hub

**[healthxllm.netlify.app](https://healthxllm.netlify.app)** · [Browse Models](https://healthxllm.netlify.app/models.html) · [Browse Datasets](https://healthxllm.netlify.app/datasets.html)

An open hub for health AI: browse 47 LLMs and 44 datasets, benchmark any model against 7 reproducible clinical evals, and contribute your results in one pull request.

> **Not medical advice, and not clinical validation.** A high score here does not make a model safe to use in patient care.

---

## What's in the hub

### 🧠 Models catalog (`/models.html`)
47 open-source LLMs for health — from specialized medical fine-tunes to general models with strong clinical performance. Each entry has: use case, "best for" summary, task tags, HuggingFace link, Ollama tag, and license.

Includes: Meditron 7B/70B, OpenBioLLM 8B/70B, MedGemma 4B/27B, BioMistral, Med42, BioBERT, ClinicalBERT, PubMedBERT, GatorTron, MedCPT, CheXbert, ClinicalT5, LLaMA 3 Aloe, and more.

### 📊 Datasets catalog (`/datasets.html`)
44 openly licensed datasets for training, fine-tuning, and evaluating health AI — spanning Medical QA, NER, Radiology, Clinical Records, Drug Safety, Genomics, Instruction Tuning, and Literature.

Includes: MedQA, MedMCQA, PubMedQA, PubHealth, NCBI Disease, MIMIC-IV, CheXpert, Medical-O1 Reasoning, HealthCareMagic 100k, EPFL Guidelines, LOINC, ICD-10, and more.

### 📈 Evals (7 reproducible health benchmarks)

| Eval | Measures | Dataset | Metric |
|---|---|---|---|
| `med-knowledge` | Medical fact recall | MedMCQA | Accuracy |
| `clinical-reasoning` | Patient vignette → diagnosis | MedQA USMLE | Accuracy |
| `evidence-reasoning` | Abstract → yes/no/maybe | PubMedQA | Accuracy |
| `claim-verification` | Health claim true/false/mixture/unproven | PubHealth | Accuracy |
| `entity-extraction` | Disease mentions in a passage | NCBI Disease | F1 |
| `json-reliability` | Valid JSON output rate | Extraction replies | % valid |
| `consistency` | Same answer with shuffled options | MedMCQA | % consistent |

The **health rating** is the unweighted mean of all seven. See [docs/METHODOLOGY.md](docs/METHODOLOGY.md) for details and known limits.

---

## Add a model and submit scores

Any open model that runs in [Ollama](https://ollama.com) can be evaluated. Full guide: **[docs/ADDING_A_MODEL.md](docs/ADDING_A_MODEL.md)**

**Quick start:**

```bash
# 1. Fork and clone the repo
git clone https://github.com/<your-handle>/healthllm && cd healthllm

# 2. Create a model file
cp data/models/mistral-7b.json data/models/my-model-7b.json
# → edit id, name, developer, params_b, license, ollama, hf, medical_tuned

# 3. Install eval dependencies
pip install -r evals/requirements.txt

# 4. Pull the model in Ollama
ollama pull my-model:7b

# 5. Run all 7 evals (takes 20–60 min depending on hardware)
python evals/run_eval.py \
  --model my-model-7b \
  --hardware "M2 Pro, 16 GB" \
  --submitted-by your-github-handle

# 6. Validate and preview the site
npm run check    # validates all data files
npm start        # serves the site at http://localhost:4173

# 7. Open a pull request with:
#    data/models/my-model-7b.json
#    data/results/my-model-7b.json
```

**Rules for a comparable submission:**
- Keep `--samples 100` and `--seed 42` (the defaults) so every model answers the same questions
- Run all 7 evals — the health rating only appears when all seven scores are present
- Do not edit the results file by hand; if a score looks wrong, open an issue
- Include `--hardware` so speed numbers are interpretable

**Useful flags:**

| Flag | What it does |
|---|---|
| `--dry-run` | Fake model + built-in fixtures — verifies setup without Ollama |
| `--evals med-knowledge consistency` | Run only specific evals |
| `--samples 20` | Quick trial run (do not submit) |
| `--inspect med-knowledge` | Print first dataset row to debug field changes |
| `--host http://other-machine:11434` | Use a remote Ollama server |

**List a model without scores:**
Submit only `data/models/my-model.json`. It appears in the catalog, and anyone can add results later.

---

## Run the site locally

Node 18+ required. No dependencies to install.

```bash
npm start
# → validates data, writes build/, serves at http://localhost:4173
```

Validation only (CI check):

```bash
npm run check
```

Run the eval unit tests:

```bash
python -m unittest discover evals
```

---

## Repo layout

```
data/
  evals.json             eval definitions + site examples
  models/*.json          one file per leaderboard model (name, params, license, ollama tag)
  results/*.json         eval scores, written by run_eval.py
  health-models.json     full models catalog (47 entries, shown on /models.html)
  health-datasets.json   full datasets catalog (44 entries, shown on /datasets.html)

evals/
  run_eval.py            eval runner — downloads datasets, queries Ollama, writes results
  test_run_eval.py       unit tests for parsing and scoring
  requirements.txt       pip dependencies (datasets>=2.19)

site/
  index.html             home page
  models.html            models catalog page
  datasets.html          datasets catalog page
  app.js                 leaderboard rendering (index.html)
  catalog.js             filter + card rendering (models/datasets pages)
  styles.css             shared styles

scripts/
  build.mjs              validates data, bundles data.json, copies site → build/
  serve.mjs              local dev server

docs/
  ADDING_A_MODEL.md      full step-by-step guide for submitting a model
  METHODOLOGY.md         how the health rating is computed and its known limits
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Model submissions, new evals with openly licensed data, and documentation fixes are all welcome.

For new evals, open an issue first. Requirements: openly licensed dataset (no access request), automatic metric (no judge model), entry in `data/evals.json`, loader + scorer in `run_eval.py`.

## Licence

Code and site: [MIT](LICENSE). Datasets keep their own licences and are downloaded at run time — no dataset rows are stored in this repo.
