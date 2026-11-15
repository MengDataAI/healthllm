"""
Add language tags to health-models.json and health-datasets.json,
then re-seed Supabase.

Run:
    python3 scripts/add_languages.py
"""
import json, os, urllib.request, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ── Language rules (checked against model/dataset name + tags) ───────────────
MULTILINGUAL_KEYWORDS = ["multilingual", "qwen", "gemma", "llama", "mistral", "phi",
                          "deepseek", "bloom", "falcon", "yi-", "baichuan", "glm",
                          "aya", "mbert", "xlm", "mt5", "mT0"]
CHINESE_KEYWORDS = ["chinese", "zh", "baichuan", "chatglm", "qwen"]
SPANISH_KEYWORDS = ["spanish", "es-", "beto", "roberta-es"]
FRENCH_KEYWORDS = ["french", "camembert", "fr-"]
ARABIC_KEYWORDS = ["arabic", "ar-", "camelbert", "arbert"]

def infer_languages(entry: dict) -> list:
    name = (entry.get("name") or "").lower()
    hf = (entry.get("hf") or "").lower()
    tags = [t.lower() for t in (entry.get("tags") or [])]
    text = f"{name} {hf} {' '.join(tags)}"

    langs = set()

    # Already has explicit language tag?
    for t in tags:
        if t in ("english", "multilingual", "chinese", "spanish", "french", "arabic", "german"):
            langs.add(t.capitalize())

    # Infer from keywords
    if any(k in text for k in MULTILINGUAL_KEYWORDS):
        langs.add("Multilingual")
    if any(k in text for k in CHINESE_KEYWORDS):
        langs.add("Chinese")
    if any(k in text for k in SPANISH_KEYWORDS):
        langs.add("Spanish")
    if any(k in text for k in FRENCH_KEYWORDS):
        langs.add("French")
    if any(k in text for k in ARABIC_KEYWORDS):
        langs.add("Arabic")

    # Default to English
    langs.add("English")

    # If multilingual, don't just show English
    result = sorted(langs)
    return result


def process_file(path: Path) -> list:
    data = json.loads(path.read_text())
    for entry in data:
        if not entry.get("language"):
            entry["language"] = infer_languages(entry)
    path.write_text(json.dumps(data, indent=2))
    print(f"Updated {path.name} ({len(data)} entries)")
    return data


models = process_file(ROOT / "data" / "health-models.json")
datasets = process_file(ROOT / "data" / "health-datasets.json")

# ── Re-seed Supabase ──────────────────────────────────────────────────────────
url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
key = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not url or not key:
    print("\nSkipping Supabase push — set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_KEY")
    sys.exit(0)

HEADERS = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",
}

def upsert(table, rows):
    endpoint = f"{url}/rest/v1/{table}"
    for i in range(0, len(rows), 100):
        batch = rows[i:i+100]
        req = urllib.request.Request(endpoint, data=json.dumps(batch).encode(), headers=HEADERS, method="POST")
        with urllib.request.urlopen(req) as r: r.read()
        print(f"  {table}: {min(i+100, len(rows))}/{len(rows)}", end="\r")
    print()

print("\nPushing to Supabase...")
upsert("health_models", models)
upsert("health_datasets", datasets)
print("Done.")
