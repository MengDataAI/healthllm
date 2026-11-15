import { createClient } from "@/utils/supabase/server";
import CatalogClient from "@/components/CatalogClient";
import type { HealthModel } from "@/types";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Health LLMs — HealthLLM",
  description: "Browse open health LLMs — Meditron, OpenBioLLM, MedGemma, BioBERT and more.",
};

export default async function ModelsPage() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("health_models")
    .select("*")
    .order("featured", { ascending: false })
    .order("name");

  const models: HealthModel[] = data ?? [];

  return (
    <>
      <div className="page-hero">
        <div className="wrap">
          <p className="eyebrow-sm">Browse · {models.length} models</p>
          <h1 className="page-title">Health LLMs</h1>
          <p className="page-subtitle">
            Open models for clinical reasoning, medical QA, NER, radiology, and more.
            Each with use case, HuggingFace link, and license.
          </p>
        </div>
      </div>
      <CatalogClient type="models" items={models} />
    </>
  );
}
