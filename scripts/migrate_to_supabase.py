"""
Seed Supabase with data from the existing JSON catalog files.
Uses the REST API directly (urllib) — no Python supabase client needed.

Usage:
    SUPABASE_URL=https://... SUPABASE_SERVICE_KEY=sb_secret_... python scripts/migrate_to_supabase.py
"""

import json, os, sys, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent

url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    sys.exit(
        "Set SUPABASE_URL and SUPABASE_SERVICE_KEY env vars.\n"
        "Example:\n"
        "  SUPABASE_URL=https://inqdudvzrkehjcmflbpg.supabase.co \\\n"
        "  SUPABASE_SERVICE_KEY=sb_secret_... \\\n"
        "  python scripts/migrate_to_supabase.py"
    )

url = url.rstrip("/")

HEADERS = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=representation",
}


def upsert_batch(table, rows):
    endpoint = f"{url}/rest/v1/{table}"
    for i in range(0, len(rows), 100):
        batch = rows[i : i + 100]
        body = json.dumps(batch).encode()
        req = urllib.request.Request(endpoint, data=body, headers=HEADERS, method="POST")
        try:
            with urllib.request.urlopen(req) as resp:
                resp.read()
            hi = min(i + 100, len(rows))
            print(f"  {table}: upserted rows {i + 1}–{hi}")
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            sys.exit(f"HTTP {e.code} upserting {table} rows {i+1}+: {err}")


# ── Load JSON files ────────────────────────────────────────────────────────────
models_path = ROOT / "data" / "health-models.json"
datasets_path = ROOT / "data" / "health-datasets.json"

if not models_path.exists():
    sys.exit(f"Not found: {models_path}")
if not datasets_path.exists():
    sys.exit(f"Not found: {datasets_path}")

models = json.loads(models_path.read_text())
datasets = json.loads(datasets_path.read_text())

print(f"Loaded {len(models)} models, {len(datasets)} datasets")

print("\nMigrating models...")
upsert_batch("health_models", models)

print("\nMigrating datasets...")
upsert_batch("health_datasets", datasets)

print(f"\nDone. {len(models)} models + {len(datasets)} datasets seeded into Supabase.")
