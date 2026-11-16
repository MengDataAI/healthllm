"use client";
import { useState, useMemo } from "react";
import type { HealthModel, HealthDataset } from "@/types";
import ModelCard from "./ModelCard";
import DatasetCard from "./DatasetCard";

type Props =
  | { type: "models"; items: HealthModel[] }
  | { type: "datasets"; items: HealthDataset[] };

export default function CatalogClient(props: Props) {
  const [search, setSearch] = useState("");
  const [activeTags, setActiveTags] = useState<Set<string>>(new Set());
  const [medicalOnly, setMedicalOnly] = useState(false);
  const [licenseFilter, setLicenseFilter] = useState("all");
  const [sizeFilter, setSizeFilter] = useState("all");
  const [accessFilter, setAccessFilter] = useState("all");
  const [languageFilter, setLanguageFilter] = useState("all");

  // Build language list
  const allLanguages = useMemo(() => {
    const langs = new Set<string>();
    props.items.forEach((item) => (item.language || []).forEach((l) => langs.add(l)));
    return Array.from(langs).sort();
  }, [props.items]);

  // Build tag list
  const allTags = useMemo(() => {
    const counts: Record<string, number> = {};
    props.items.forEach((item) => {
      (item.tags || []).forEach((t) => { counts[t] = (counts[t] || 0) + 1; });
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 30)
      .map(([t]) => t);
  }, [props.items]);

  const toggleTag = (tag: string) => {
    setActiveTags((prev) => {
      const next = new Set(prev);
      next.has(tag) ? next.delete(tag) : next.add(tag);
      return next;
    });
  };

  const clearAll = () => {
    setSearch("");
    setActiveTags(new Set());
    setMedicalOnly(false);
    setLicenseFilter("all");
    setSizeFilter("all");
    setAccessFilter("all");
    setLanguageFilter("all");
  };

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return props.items.filter((item) => {
      if (q && !JSON.stringify(item).toLowerCase().includes(q)) return false;
      if (activeTags.size > 0 && !item.tags?.some((t) => activeTags.has(t))) return false;
      if (languageFilter !== "all" && !(item.language || []).includes(languageFilter)) return false;

      if (props.type === "models") {
        const m = item as HealthModel;
        if (medicalOnly && !m.medical_tuned) return false;
        if (licenseFilter !== "all" && m.license_type !== licenseFilter) return false;
        if (sizeFilter !== "all" && m.params_size !== sizeFilter) return false;
      }

      if (props.type === "datasets") {
        const d = item as HealthDataset;
        if (accessFilter !== "all" && d.access !== accessFilter) return false;
      }

      return true;
    });
  }, [props.items, props.type, search, activeTags, medicalOnly, licenseFilter, sizeFilter, accessFilter, languageFilter]);

  return (
    <div className="wrap catalog-layout">
      {/* Sidebar */}
      <aside className="catalog-sidebar">
        <div className="sidebar-header">
          <span className="sidebar-title">Filters</span>
          <button className="clear-link" onClick={clearAll}>Clear all</button>
        </div>

        <div className="sidebar-search">
          <div className="search-wrap" style={{ flex: "none", width: "100%" }}>
            <svg className="search-icon" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <circle cx="8.5" cy="8.5" r="5.5" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M13 13l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <input
              type="search"
              placeholder={props.type === "models" ? "Search models…" : "Search datasets…"}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search"
            />
          </div>
        </div>

        {props.type === "models" && (
          <>
            <div className="filter-group">
              <label className="filter-check">
                <input
                  type="checkbox"
                  checked={medicalOnly}
                  onChange={(e) => setMedicalOnly(e.target.checked)}
                />
                Medical fine-tuned only
              </label>
            </div>
            <div className="filter-group">
              <p className="filter-group-label">License</p>
              <select value={licenseFilter} onChange={(e) => setLicenseFilter(e.target.value)}>
                <option value="all">All licenses</option>
                <option value="open-source">Open source</option>
                <option value="open-weights">Open weights</option>
              </select>
            </div>
            <div className="filter-group">
              <p className="filter-group-label">Size</p>
              <select value={sizeFilter} onChange={(e) => setSizeFilter(e.target.value)}>
                <option value="all">All sizes</option>
                <option value="tiny">Tiny (&lt;2B)</option>
                <option value="small">Small (2–8B)</option>
                <option value="medium">Medium (8–20B)</option>
                <option value="large">Large (20B+)</option>
              </select>
            </div>
          </>
        )}

        {props.type === "datasets" && (
          <div className="filter-group">
            <p className="filter-group-label">Access</p>
            <select value={accessFilter} onChange={(e) => setAccessFilter(e.target.value)}>
              <option value="all">All</option>
              <option value="open">Open</option>
              <option value="credentialed">Credentialed</option>
              <option value="gated">Gated</option>
            </select>
          </div>
        )}

        {allLanguages.length > 0 && (
          <div className="filter-group">
            <p className="filter-group-label">Language</p>
            <select value={languageFilter} onChange={(e) => setLanguageFilter(e.target.value)}>
              <option value="all">All languages</option>
              {allLanguages.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </div>
        )}

        <div className="filter-group">
          <p className="filter-group-label">Tags</p>
          <div className="tag-filter-list">
            {allTags.map((tag) => (
              <button
                key={tag}
                className={`sidebar-tag${activeTags.has(tag) ? " active" : ""}`}
                onClick={() => toggleTag(tag)}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* Grid */}
      <div>
        <div className="catalog-toolbar-row">
          <span className="result-count">
            {filtered.length} {props.type === "models" ? "models" : "datasets"}
            {filtered.length !== props.items.length && ` of ${props.items.length}`}
          </span>
        </div>

        {filtered.length === 0 ? (
          <div className="catalog-empty-state">
            <p>No results found.</p>
            <button onClick={clearAll}>Clear filters</button>
          </div>
        ) : (
          <div className="hf-grid">
            {filtered.map((item) =>
              props.type === "models" ? (
                <ModelCard key={item.id} model={item as HealthModel} />
              ) : (
                <DatasetCard key={item.id} dataset={item as HealthDataset} />
              )
            )}
          </div>
        )}
      </div>
    </div>
  );
}
