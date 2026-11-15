"""
Weekly HuggingFace catalog sync.

Searches HuggingFace for new health/medical models and datasets that are not
already in data/health-models.json and data/health-datasets.json.  Any new
entries are appended to those files.

Usage:
    python scripts/sync_hf.py              # live run
    python scripts/sync_hf.py --dry-run   # print what would be added, don't write
    python scripts/sync_hf.py --limit 50  # cap results per search query (default 200)
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from huggingface_hub import HfApi
    from huggingface_hub.utils import HfHubHTTPError
except ImportError:
    sys.exit("huggingface_hub not installed.  Run: pip install huggingface-hub")

ROOT = Path(__file__).parent.parent
MODELS_FILE = ROOT / "data" / "health-models.json"
DATASETS_FILE = ROOT / "data" / "health-datasets.json"

# ── Search tags ──────────────────────────────────────────────────────────────
MODEL_TAGS = [
    "medical",
    "healthcare",
    "clinical",
    "biomedical",
    "health",
    "medicine",
    "radiology",
    "genomics",
    "drug-discovery",
    "pubmed",
]

DATASET_TAGS = [
    "medical",
    "healthcare",
    "clinical",
    "biomedical",
    "health",
    "medicine",
    "radiology",
    "genomics",
    "drug-discovery",
    "pubmed",
    "mimic",
]

# ── License helpers ───────────────────────────────────────────────────────────
OPEN_SOURCE_LICENSES = {
    "apache-2.0", "mit", "cc-by-4.0", "cc-by-sa-4.0", "cc0-1.0",
    "bsd-2-clause", "bsd-3-clause", "gpl-3.0", "lgpl-3.0", "mpl-2.0",
    "openrail", "bigscience-openrail-m", "creativeml-openrail-m",
    "cc-by-nc-4.0", "cc-by-nc-sa-4.0",
}
OPEN_WEIGHTS_KEYWORDS = {"llama", "gemma", "qwen", "mistral", "falcon", "phi"}


def license_type(license_str: str) -> str:
    if not license_str:
        return "open-weights"
    s = license_str.lower()
    if any(s == lic for lic in OPEN_SOURCE_LICENSES):
        return "open-source"
    if any(kw in s for kw in OPEN_WEIGHTS_KEYWORDS):
        return "open-weights"
    return "open-source"


# ── Param helpers ─────────────────────────────────────────────────────────────
def parse_params(model_id: str, card_data) -> tuple[str, str]:
    """Return (params label like '7B', params_size bucket)."""
    # Try safetensors / model card metadata first
    param_b = None
    if card_data:
        raw = getattr(card_data, "safetensors", None)
        if raw and hasattr(raw, "total"):
            param_b = raw.total / 1e9

    if param_b is None:
        # Guess from the repo name
        m = re.search(r"(\d+(?:\.\d+)?)b", model_id.lower())
        if m:
            param_b = float(m.group(1))

    if param_b is None:
        return "?", "small"

    if param_b < 2:
        label, size = f"{param_b:.1f}B", "tiny"
    elif param_b < 8:
        label, size = f"{int(param_b)}B", "small"
    elif param_b < 20:
        label, size = f"{int(param_b)}B", "medium"
    elif param_b < 50:
        label, size = f"{int(param_b)}B", "large"
    else:
        label, size = f"{int(param_b)}B", "large"
    return label, size


# ── Tag helpers ───────────────────────────────────────────────────────────────
HF_TAG_MAP = {
    "question-answering": "medical-qa",
    "text-generation": "general",
    "token-classification": "ner",
    "text-classification": "general",
    "summarization": "summarization",
    "translation": "multilingual",
    "image-classification": "radiology",
    "medical": "medical-qa",
    "clinical": "clinical-reasoning",
    "biomedical": "biomedical",
    "radiology": "radiology",
    "genomics": "genomics",
    "drug": "drug-safety",
    "ehr": "ehr",
    "pubmed": "biomedical",
}


def infer_model_tags(hf_tags: list[str], model_id: str) -> list[str]:
    out = set()
    combined = " ".join(hf_tags + [model_id]).lower()
    for src, dst in HF_TAG_MAP.items():
        if src in combined:
            out.add(dst)
    if "bert" in combined:
        out.add("bert-based")
    if "llama" in combined:
        out.add("llama-based")
    if "mistral" in combined:
        out.add("mistral-based")
    if "gemma" in combined:
        out.add("gemma-based")
    if not out:
        out.add("general")
    return sorted(out)


DATASET_TYPE_MAP = {
    "question-answering": "Medical QA",
    "medical": "Medical QA",
    "clinical": "Clinical Records",
    "ner": "NER",
    "token-classification": "NER",
    "radiology": "Radiology",
    "summarization": "Summarization",
    "text-classification": "NLI",
    "natural-language-inference": "NLI",
    "genomics": "Genomics",
    "drug": "Drug Safety",
    "instruction": "Instruction Tuning",
    "dialogue": "Dialogue",
    "biomedical": "Biomedical Literature",
}


def infer_dataset_type(hf_tags: list[str], ds_id: str) -> str:
    combined = " ".join(hf_tags + [ds_id]).lower()
    for src, dst in DATASET_TYPE_MAP.items():
        if src in combined:
            return dst
    return "Medical QA"


def infer_dataset_task(ds_type: str) -> str:
    return {
        "Medical QA": "medical-qa",
        "Clinical Records": "clinical-records",
        "NER": "ner",
        "Radiology": "radiology",
        "Summarization": "summarization",
        "NLI": "nli",
        "Genomics": "genomics",
        "Drug Safety": "drug-safety",
        "Instruction Tuning": "instruction-tuning",
        "Dialogue": "dialogue",
        "Biomedical Literature": "biomedical-literature",
    }.get(ds_type, "medical-qa")


# ── Slug helpers ──────────────────────────────────────────────────────────────
def repo_to_id(repo_id: str) -> str:
    """'org/Model-Name-7B' → 'org-model-name-7b'"""
    slug = repo_id.replace("/", "-").lower()
    slug = re.sub(r"[^a-z0-9.\-]", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug


# ── Usecase / strength generators ────────────────────────────────────────────
def model_usecase(name: str, tags: list[str], card_summary: str) -> str:
    if card_summary and len(card_summary) > 30:
        # First sentence only, capped at 160 chars
        sentence = card_summary.split(".")[0].strip()
        if 20 < len(sentence) < 180:
            return sentence + "."
    dominant = tags[0] if tags else "general"
    return f"Open health LLM suitable for {dominant.replace('-', ' ')} tasks."


def model_strength(name: str, tags: list[str]) -> str:
    parts = [t.replace("-", " ") for t in tags[:3]]
    return ", ".join(parts).capitalize() + "." if parts else "General health AI tasks."


def dataset_description(name: str, ds_type: str, card_summary: str) -> str:
    if card_summary and len(card_summary) > 30:
        sentence = card_summary.split(".")[0].strip()
        if 20 < len(sentence) < 200:
            return sentence + "."
    return f"A {ds_type.lower()} dataset for health AI research and evaluation."


def dataset_usecase(ds_type: str) -> str:
    return {
        "Medical QA": "Evaluate and train models on medical question answering tasks.",
        "Clinical Records": "Train models on real clinical documentation and EHR data.",
        "NER": "Fine-tune models for biomedical named entity recognition.",
        "Radiology": "Train and evaluate models on radiology reports and imaging data.",
        "Summarization": "Benchmark clinical summarization capabilities.",
        "NLI": "Evaluate natural language inference on biomedical text.",
        "Genomics": "Research and train models on genomics and sequencing data.",
        "Drug Safety": "Evaluate drug interaction, adverse event, and safety tasks.",
        "Instruction Tuning": "Fine-tune general LLMs for health-specific instruction following.",
        "Dialogue": "Train conversational models for patient-provider dialogue.",
        "Biomedical Literature": "Train models to reason over scientific and clinical literature.",
    }.get(ds_type, "General health AI research and model evaluation.")


# ── Card summary helper ───────────────────────────────────────────────────────
def card_summary(card_data) -> str:
    try:
        text = getattr(card_data, "text", "") or ""
        # Strip markdown headers and blank lines
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
        for line in lines:
            if len(line) > 40:
                return line
    except Exception:
        pass
    return ""


# ── Main sync logic ───────────────────────────────────────────────────────────
def load_json(path: Path) -> list:
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def save_json(path: Path, data: list):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def sync_models(api: HfApi, existing_hf: set[str], limit: int, dry_run: bool) -> list[dict]:
    new_entries = []
    seen_in_run: set[str] = set()

    for tag in MODEL_TAGS:
        print(f"  Searching models tag={tag!r} ...")
        try:
            results = api.list_models(
                search=tag,
                sort="downloads",
                direction=-1,
                limit=limit,
            )
        except (HfHubHTTPError, TypeError) as e:
            print(f"    HF API error: {e}", file=sys.stderr)
            continue

        for model in results:
            hf_id = model.id
            if hf_id in existing_hf or hf_id in seen_in_run:
                continue
            seen_in_run.add(hf_id)

            # Try to fetch model card for description
            try:
                card_data = api.model_info(hf_id, files_metadata=False)
                summary = card_summary(card_data.card_data)
            except Exception:
                card_data = None
                summary = ""

            hf_tags = list(getattr(model, "tags", []) or [])
            license_val = getattr(model, "license", None) or ""
            params_label, params_size = parse_params(hf_id, card_data)
            tags = infer_model_tags(hf_tags, hf_id)
            med_tuned = any(
                t in " ".join(hf_tags + [hf_id]).lower()
                for t in ("medical", "clinical", "biomedical", "health", "pubmed", "meditron", "med42")
            )

            entry = {
                "id": repo_to_id(hf_id),
                "name": model.modelId.split("/")[-1].replace("-", " ").replace("_", " "),
                "developer": hf_id.split("/")[0],
                "params": params_label,
                "params_size": params_size,
                "medical_tuned": med_tuned,
                "license": license_val or "unknown",
                "license_type": license_type(license_val),
                "hf": hf_id,
                "ollama": None,
                "specialty": [tags[0]] if tags else ["general"],
                "usecase": model_usecase(hf_id, tags, summary),
                "strength": model_strength(hf_id, tags),
                "tags": tags,
                "featured": False,
            }
            new_entries.append(entry)
            print(f"    + model {hf_id}")

    return new_entries


def sync_datasets(api: HfApi, existing_hf: set[str], limit: int, dry_run: bool) -> list[dict]:
    new_entries = []
    seen_in_run: set[str] = set()

    for tag in DATASET_TAGS:
        print(f"  Searching datasets tag={tag!r} ...")
        try:
            results = api.list_datasets(
                search=tag,
                sort="downloads",
                direction=-1,
                limit=limit,
            )
        except (HfHubHTTPError, TypeError) as e:
            print(f"    HF API error: {e}", file=sys.stderr)
            continue

        for ds in results:
            hf_id = ds.id
            if hf_id in existing_hf or hf_id in seen_in_run:
                continue
            seen_in_run.add(hf_id)

            hf_tags = list(getattr(ds, "tags", []) or [])
            license_val = getattr(ds, "license", None) or ""

            # Fetch card for description
            try:
                info = api.dataset_info(hf_id)
                summary = card_summary(info.card_data)
                size_str = ""
                if hasattr(info, "card_data") and info.card_data:
                    size_str = str(getattr(info.card_data, "size_categories", [""])[0] or "")
            except Exception:
                summary = ""
                size_str = ""

            ds_type = infer_dataset_type(hf_tags, hf_id)
            task = infer_dataset_task(ds_type)
            access = "credentialed" if any(
                k in hf_id.lower() for k in ("mimic", "physionet", "credentialed")
            ) else "open"

            entry = {
                "id": repo_to_id(hf_id),
                "name": hf_id.split("/")[-1].replace("-", " ").replace("_", " "),
                "type": ds_type,
                "size": size_str or "varies",
                "task": task,
                "access": access,
                "license": license_val or "unknown",
                "hf": hf_id,
                "specialty": ["general-medicine"],
                "description": dataset_description(hf_id, ds_type, summary),
                "usecase": dataset_usecase(ds_type),
                "tags": infer_model_tags(hf_tags, hf_id),
                "featured": False,
            }
            new_entries.append(entry)
            print(f"    + dataset {hf_id}")

    return new_entries


def main():
    parser = argparse.ArgumentParser(description="Sync HuggingFace health catalog")
    parser.add_argument("--dry-run", action="store_true", help="Print changes but do not write files")
    parser.add_argument("--limit", type=int, default=200, help="Max results per search tag (default 200)")
    args = parser.parse_args()

    api = HfApi()

    # Load existing catalogs
    existing_models = load_json(MODELS_FILE)
    existing_datasets = load_json(DATASETS_FILE)

    existing_model_hf = {m["hf"] for m in existing_models if m.get("hf")}
    existing_dataset_hf = {d["hf"] for d in existing_datasets if d.get("hf")}

    print(f"Existing: {len(existing_models)} models, {len(existing_datasets)} datasets")

    print("\nSyncing models...")
    new_models = sync_models(api, existing_model_hf, args.limit, args.dry_run)

    print("\nSyncing datasets...")
    new_datasets = sync_datasets(api, existing_dataset_hf, args.limit, args.dry_run)

    print(f"\nFound {len(new_models)} new models, {len(new_datasets)} new datasets")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        if new_models:
            print("New models:")
            for m in new_models:
                print(f"  {m['hf']}")
        if new_datasets:
            print("New datasets:")
            for d in new_datasets:
                print(f"  {d['hf']}")
        return

    if new_models:
        updated_models = existing_models + new_models
        save_json(MODELS_FILE, updated_models)
        print(f"Wrote {MODELS_FILE} ({len(updated_models)} total models)")

    if new_datasets:
        updated_datasets = existing_datasets + new_datasets
        save_json(DATASETS_FILE, updated_datasets)
        print(f"Wrote {DATASETS_FILE} ({len(updated_datasets)} total datasets)")

    # Output counts for the CI step summary
    total_new = len(new_models) + len(new_datasets)
    print(f"\nSYNC_NEW_MODELS={len(new_models)}")
    print(f"SYNC_NEW_DATASETS={len(new_datasets)}")
    print(f"SYNC_TOTAL_NEW={total_new}")


if __name__ == "__main__":
    main()
