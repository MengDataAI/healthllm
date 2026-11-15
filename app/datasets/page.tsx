import { createClient } from "@/utils/supabase/server";
import CatalogClient from "@/components/CatalogClient";
import type { HealthDataset } from "@/types";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Health Datasets — HealthLLM",
  description: "Browse openly licensed health datasets for medical QA, NER, radiology, clinical records, and more.",
};

export default async function DatasetsPage() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("health_datasets")
    .select("*")
    .order("featured", { ascending: false })
    .order("name");

  const datasets: HealthDataset[] = data ?? [];

  return (
    <>
      <div className="page-hero">
        <div className="wrap">
          <p className="eyebrow-sm">Browse · {datasets.length} datasets</p>
          <h1 className="page-title">Health Datasets</h1>
          <p className="page-subtitle">
            Openly licensed datasets for training, fine-tuning, and evaluating health AI —
            spanning clinical records, medical QA, NER, radiology, drug safety, genomics, and more.
          </p>
        </div>
      </div>
      <CatalogClient type="datasets" items={datasets} />
    </>
  );
}
