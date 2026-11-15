"""
Weekly HuggingFace catalog sync.

Uses the HuggingFace REST API directly (no huggingface_hub library required)
to search for new health/medical models and datasets not already in the catalog.

Usage:
    python scripts/sync_hf.py              # live run
    python scripts/sync_hf.py --dry-run   # print what would be added, don't write
    python scripts/sync_hf.py --limit 50  # cap results per search query (default 200)
"""

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent.parent
MODELS_FILE = ROOT / "data" / "health-models.json"
DATASETS_FILE = ROOT / "data" / "health-datasets.json"

HF_API = "https://huggingface.co/api"

# ── Search queries ────────────────────────────────────────────────────────────
MODEL_QUERIES = [
    "medical llm",
    "clinical llm",
    "biomedical language model",
    "health llm",
    "medical bert",
    "clinical bert",
    "pubmed",
    "radiology ai",
    "drug discovery model",
    "genomics language model",
]

DATASET_QUERIES = [
    "medical qa",
    "clinical nlp",
    "biomedical dataset",
    "health dataset",
    "pubmed dataset",
    "radiology dataset",
    "drug safety dataset",
    "genomics dataset",
    "mimic clinical",
    "medical ner",
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
    if s in OPEN_SOURCE_LICENSES:
        return "open-source"
    if any(kw in s for kw in OPEN_WEIGHTS_KEYWORDS):
        return "open-weights"
    return "open-source"


# ── Param helpers ─────────────────────────────────────────────────────────────
def parse_params(model_id: str) -> tuple[str, str]:
    m = re.search(r"(\d+(?:\.\d+)?)b", model_id.lower())
    if m:
        param_b = float(m.group(1))
        if param_b < 2:
            return f"{param_b:.1f}B", "tiny"
        elif param_b < 8:
            return f"{int(param_b)}B", "small"
        elif param_b < 20:
            return f"{int(param_b)}B", "medium"
        else:
            return f"{int(param_b)}B", "large"
    return "?", "small"


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


def infer_model_tags(hf_tags: list, model_id: str) -> list[str]:
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


def infer_dataset_type(hf_tags: list, ds_id: str) -> str:
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
    slug = repo_id.replace("/", "-").lower()
    slug = re.sub(r"[^a-z0-9.\-]", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug


# ── Usecase / strength generators ────────────────────────────────────────────
def model_usecase(tags: list, card_text: str) -> str:
    if card_text and len(card_text) > 30:
        sentence = card_text.split(".")[0].strip()
        if 20 < len(sentence) < 180:
            return sentence + "."
    dominant = tags[0] if tags else "general"
    return f"Open health LLM suitable for {dominant.replace('-', ' ')} tasks."


def model_strength(tags: list) -> str:
    parts = [t.replace("-", " ") for t in tags[:3]]
    return ", ".join(parts).capitalize() + "." if parts else "General health AI tasks."


def dataset_description(ds_type: str, card_text: str) -> str:
    if card_text and len(card_text) > 30:
        sentence = card_text.split(".")[0].strip()
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


# ── HuggingFace REST API helpers ──────────────────────────────────────────────
def hf_get(endpoint: str, params: dict) -> list:
    """Call HuggingFace REST API, return parsed JSON list."""
    url = f"{HF_API}/{endpoint}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "healthllm-sync/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"    HTTP error for {endpoint}: {e}", file=sys.stderr)
        return []


# ── Main sync logic ───────────────────────────────────────────────────────────
def load_json(path: Path) -> list:
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def save_json(path: Path, data: list):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def sync_models(existing_hf: set, limit: int) -> list[dict]:
    new_entries = []
    seen_in_run: set = set()

    for query in MODEL_QUERIES:
        print(f"  Searching models: {query!r} ...")
        items = hf_get("models", {
            "search": query,
            "sort": "downloads",
            "direction": -1,
            "limit": limit,
            "full": "false",
        })
        time.sleep(0.3)  # be polite to the API

        for model in items:
            hf_id = model.get("id") or model.get("modelId")
            if not hf_id:
                continue
            if hf_id in existing_hf or hf_id in seen_in_run:
                continue
            seen_in_run.add(hf_id)

            hf_tags = model.get("tags") or []
            license_val = model.get("license") or ""
            params_label, params_size = parse_params(hf_id)
            tags = infer_model_tags(hf_tags, hf_id)
            med_tuned = any(
                t in " ".join(hf_tags + [hf_id]).lower()
                for t in ("medical", "clinical", "biomedical", "health", "pubmed", "meditron", "med42")
            )

            # Fetch card description (best-effort)
            card_text = ""
            try:
                info = hf_get(f"models/{hf_id}", {})
                if isinstance(info, dict):
                    card_text = (info.get("cardData") or {}).get("summary", "") or ""
            except Exception:
                pass

            entry = {
                "id": repo_to_id(hf_id),
                "name": hf_id.split("/")[-1].replace("-", " ").replace("_", " "),
                "developer": hf_id.split("/")[0],
                "params": params_label,
                "params_size": params_size,
                "medical_tuned": med_tuned,
                "license": license_val or "unknown",
                "license_type": license_type(license_val),
                "hf": hf_id,
                "ollama": None,
                "specialty": [tags[0]] if tags else ["general"],
                "usecase": model_usecase(tags, card_text),
                "strength": model_strength(tags),
                "tags": tags,
                "featured": False,
            }
            new_entries.append(entry)
            print(f"    + model {hf_id}")

    return new_entries


def sync_datasets(existing_hf: set, limit: int) -> list[dict]:
    new_entries = []
    seen_in_run: set = set()

    for query in DATASET_QUERIES:
        print(f"  Searching datasets: {query!r} ...")
        items = hf_get("datasets", {
            "search": query,
            "sort": "downloads",
            "direction": -1,
            "limit": limit,
            "full": "false",
        })
        time.sleep(0.3)

        for ds in items:
            hf_id = ds.get("id") or ds.get("datasetId")
            if not hf_id:
                continue
            if hf_id in existing_hf or hf_id in seen_in_run:
                continue
            seen_in_run.add(hf_id)

            hf_tags = ds.get("tags") or []
            license_val = ds.get("license") or ""
            ds_type = infer_dataset_type(hf_tags, hf_id)
            task = infer_dataset_task(ds_type)
            access = "credentialed" if any(
                k in hf_id.lower() for k in ("mimic", "physionet")
            ) else "open"

            card_text = ""
            try:
                info = hf_get(f"datasets/{hf_id}", {})
                if isinstance(info, dict):
                    card_text = (info.get("cardData") or {}).get("summary", "") or ""
            except Exception:
                pass

            entry = {
                "id": repo_to_id(hf_id),
                "name": hf_id.split("/")[-1].replace("-", " ").replace("_", " "),
                "type": ds_type,
                "size": "varies",
                "task": task,
                "access": access,
                "license": license_val or "unknown",
                "hf": hf_id,
                "specialty": ["general-medicine"],
                "description": dataset_description(ds_type, card_text),
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
    parser.add_argument("--limit", type=int, default=200, help="Max results per search query (default 200)")
    args = parser.parse_args()

    existing_models = load_json(MODELS_FILE)
    existing_datasets = load_json(DATASETS_FILE)

    existing_model_hf = {m["hf"] for m in existing_models if m.get("hf")}
    existing_dataset_hf = {d["hf"] for d in existing_datasets if d.get("hf")}

    print(f"Existing: {len(existing_models)} models, {len(existing_datasets)} datasets")

    print("\nSyncing models...")
    new_models = sync_models(existing_model_hf, args.limit)

    print("\nSyncing datasets...")
    new_datasets = sync_datasets(existing_dataset_hf, args.limit)

    print(f"\nFound {len(new_models)} new models, {len(new_datasets)} new datasets")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        for m in new_models:
            print(f"  model: {m['hf']}")
        for d in new_datasets:
            print(f"  dataset: {d['hf']}")
        # Still emit counts so the workflow can read them
        print(f"\nSYNC_NEW_MODELS={len(new_models)}")
        print(f"SYNC_NEW_DATASETS={len(new_datasets)}")
        print(f"SYNC_TOTAL_NEW={len(new_models) + len(new_datasets)}")
        return

    if new_models:
        save_json(MODELS_FILE, existing_models + new_models)
        print(f"Wrote {MODELS_FILE} ({len(existing_models) + len(new_models)} total models)")

    if new_datasets:
        save_json(DATASETS_FILE, existing_datasets + new_datasets)
        print(f"Wrote {DATASETS_FILE} ({len(existing_datasets) + len(new_datasets)} total datasets)")

    print(f"\nSYNC_NEW_MODELS={len(new_models)}")
    print(f"SYNC_NEW_DATASETS={len(new_datasets)}")
    print(f"SYNC_TOTAL_NEW={len(new_models) + len(new_datasets)}")


if __name__ == "__main__":
    main()
