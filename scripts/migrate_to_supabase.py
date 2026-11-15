"""
Seed Supabase with data from the existing JSON catalog files.

Usage:
    pip install supabase
    SUPABASE_URL=https://... SUPABASE_SERVICE_KEY=... python scripts/migrate_to_supabase.py

The SERVICE key (not publishable key) is required to bypass RLS for bulk inserts.
Get it from: Supabase dashboard → Settings → API → service_role key
"""

import json, os, sys
from pathlib import Path

try:
    from supabase import create_client
except ImportError:
    sys.exit("Run: pip install supabase")

ROOT = Path(__file__).parent.parent

url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    sys.exit(
        "Set SUPABASE_URL and SUPABASE_SERVICE_KEY env vars.\n"
        "Get the service key from Supabase dashboard → Settings → API → service_role"
    )

supabase = create_client(url, key)

# ── Load JSON files ────────────────────────────────────────────────────────────
models = json.loads((ROOT / "data" / "health-models.json").read_text())
datasets = json.loads((ROOT / "data" / "health-datasets.json").read_text())

print(f"Loaded {len(models)} models, {len(datasets)} datasets")

# ── Upsert in batches of 100 ───────────────────────────────────────────────────
def upsert_batch(table: str, rows: list[dict]):
    for i in range(0, len(rows), 100):
        batch = rows[i:i+100]
        res = supabase.table(table).upsert(batch, on_conflict="id").execute()
        print(f"  {table}: upserted rows {i+1}–{min(i+100, len(rows))}")

print("\nMigrating models...")
upsert_batch("health_models", models)

print("\nMigrating datasets...")
upsert_batch("health_datasets", datasets)

print(f"\nDone. {len(models)} models + {len(datasets)} datasets in Supabase.")
