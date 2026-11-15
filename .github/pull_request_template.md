## What does this PR do?

<!-- Briefly describe what you're adding or changing -->

---

## Checklist

### Adding a model to the catalog (`data/health-models.json`)
- [ ] Added entry to `data/health-models.json`
- [ ] `id` is lowercase letters, digits, dots, and hyphens only
- [ ] `hf` link is correct and points to the model card
- [ ] `usecase` and `strength` are filled in (1–2 sentences each)
- [ ] `license_type` is either `"open-source"` or `"open-weights"`
- [ ] `npm run check` passes locally

### Submitting eval scores (leaderboard)
- [ ] Added `data/models/my-model.json` with model metadata
- [ ] Added `data/results/my-model.json` written by `run_eval.py` (not edited by hand)
- [ ] Used default `--samples 100` and `--seed 42`
- [ ] All 7 evals are present in the results file
- [ ] `--hardware` and `--submitted-by` are set in the results file
- [ ] `npm run check` passes locally

### Adding a dataset (`data/health-datasets.json`)
- [ ] Added entry to `data/health-datasets.json`
- [ ] `access` is either `"open"` or `"credentialed"`
- [ ] `hf` link included if available on HuggingFace
- [ ] `npm run check` passes locally

---

## Hardware (eval submissions only)

- **Machine:** <!-- e.g. M2 Pro 16 GB -->
- **Ollama version:** <!-- e.g. 0.3.12 -->
- **Approximate runtime:** <!-- e.g. 35 minutes -->
