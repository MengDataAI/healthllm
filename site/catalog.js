// Shared catalog rendering for models.html and datasets.html
(function () {
  "use strict";

  var PAGE = document.documentElement.dataset.page; // "models" or "datasets"
  var data = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function $(id) { return document.getElementById(id); }

  // ── Theme toggle (shared with main app.js) ──────────────────────────────────
  var themeBtn = $("theme");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var cur = document.documentElement.getAttribute("data-theme");
      var next = cur === "light" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  }

  // ── State ───────────────────────────────────────────────────────────────────
  var state = {
    q: "",
    tags: [],       // active tag filters (AND for models, OR by type for datasets)
    medOnly: false,
    licType: "all",
    paramsSize: "all",
    access: "all",
    sort: "default"
  };

  // ── Label maps ──────────────────────────────────────────────────────────────
  var TAG_LABELS = {
    "medical-qa": "Medical QA", "clinical-reasoning": "Clinical Reasoning",
    "biomedical": "Biomedical NLP", "ner": "NER / Extraction",
    "rag": "RAG", "clinical-notes": "Clinical Notes", "ehr": "EHR",
    "drug-safety": "Drug Safety", "research": "Research",
    "efficient": "Efficient", "edge": "Edge / Mobile",
    "general": "General Purpose", "structured-output": "Structured Output",
    "relation-extraction": "Relation Extraction", "embeddings": "Embeddings",
    "instruction-tuned": "Instruction Tuned", "safety": "Safety",
    "large-model": "Large (>30B)", "multimodal": "Multimodal",
    "dialogue": "Dialogue", "multilingual": "Multilingual",
    "bert-based": "BERT-based", "llama-based": "LLaMA-based",
    "mistral-based": "Mistral-based", "gemma-based": "Gemma-based",
    "text-generation": "Text Generation", "knowledge-graph": "Knowledge Graph",
    "entity-linking": "Entity Linking", "long-context": "Long Context",
    "open-source": "Open Source", "text-classification": "Text Classification"
  };

  var DATASET_TYPE_LABELS = {
    "Medical QA": "Medical QA", "Research QA": "Research QA", "NER": "NER",
    "Fact Checking": "Fact Checking", "Clinical Records": "Clinical Records",
    "Radiology": "Radiology", "Biomedical Literature": "Literature",
    "Drug Safety": "Drug Safety", "Dialogue": "Dialogue", "NLI": "NLI",
    "Physiological Signals": "Signals", "Genomics": "Genomics",
    "Drug-Drug Interaction": "Drug Safety", "Drug Side Effects": "Drug Safety",
    "Instruction Tuning": "Instruction Tuning", "Summarization": "Summarization"
  };

  var PARAMS_RANGES = {
    "small":  { label: "Small (< 3B)",   test: function (m) { var n = parseFloat(m.params); return n < 3; } },
    "mid":    { label: "Mid (3–15B)",     test: function (m) { var n = parseFloat(m.params); return n >= 3 && n <= 15; } },
    "large":  { label: "Large (> 15B)",   test: function (m) { var n = parseFloat(m.params); return n > 15; } }
  };

  // ── Badges ──────────────────────────────────────────────────────────────────
  function medBadge(m) {
    return m.medical_tuned
      ? '<span class="badge badge-med">medical</span>'
      : '<span class="badge badge-gen">general</span>';
  }

  function licBadge(m) {
    return m.license_type === "open-source"
      ? '<span class="badge badge-open">open source</span>'
      : '<span class="badge badge-weights">open weights</span>';
  }

  function accessBadge(d) {
    return d.access === "credentialed"
      ? '<span class="badge badge-warn">credentialed</span>'
      : '<span class="badge badge-open">open</span>';
  }

  // ── Model card ──────────────────────────────────────────────────────────────
  function modelCard(m) {
    var hfLink = m.hf
      ? '<a class="card-link" href="https://huggingface.co/' + esc(m.hf) + '" target="_blank" rel="noopener">HuggingFace ↗</a>'
      : "";
    var ollamaLink = m.ollama
      ? '<a class="card-link" href="https://ollama.com/library/' + esc(m.ollama.split(":")[0]) + '" target="_blank" rel="noopener">Ollama ↗</a>'
      : "";
    var pills = (m.tags || []).slice(0, 5).map(function (t) {
      return '<span class="pill">' + esc(TAG_LABELS[t] || t) + "</span>";
    }).join("");

    return '<article class="hf-card">' +
      '<div class="hf-card-top">' +
        '<div class="hf-card-icon">🧠</div>' +
        '<div class="hf-card-badges">' + medBadge(m) + licBadge(m) + '</div>' +
      '</div>' +
      '<h3 class="hf-card-title">' + esc(m.name) + '</h3>' +
      '<p class="hf-card-dev">' + esc(m.developer) + ' · ' + esc(m.params) + '</p>' +
      '<p class="hf-card-usecase">' + esc(m.usecase) + '</p>' +
      '<p class="hf-card-strength"><strong>Best for:</strong> ' + esc(m.strength) + '</p>' +
      '<div class="hf-card-tags">' + pills + '</div>' +
      '<div class="hf-card-links">' + hfLink + ollamaLink +
        '<span class="hf-card-lic">' + esc(m.license) + '</span>' +
      '</div>' +
    '</article>';
  }

  // ── Dataset card ─────────────────────────────────────────────────────────────
  function datasetCard(d) {
    var hfLink = d.hf
      ? '<a class="card-link" href="https://huggingface.co/datasets/' + esc(d.hf) + '" target="_blank" rel="noopener">HuggingFace ↗</a>'
      : "";
    var pills = (d.tags || []).slice(0, 5).map(function (t) {
      return '<span class="pill">' + esc(t) + "</span>";
    }).join("");
    var typeLabel = DATASET_TYPE_LABELS[d.type] || d.type;

    return '<article class="hf-card">' +
      '<div class="hf-card-top">' +
        '<div class="hf-card-icon">📊</div>' +
        '<div class="hf-card-badges">' + accessBadge(d) +
          '<span class="badge badge-type">' + esc(typeLabel) + '</span>' +
        '</div>' +
      '</div>' +
      '<h3 class="hf-card-title">' + esc(d.name) + '</h3>' +
      '<p class="hf-card-dev">' + esc(d.size) + ' · ' + esc(d.license) + '</p>' +
      '<p class="hf-card-usecase">' + esc(d.description) + '</p>' +
      '<p class="hf-card-strength"><strong>Use for:</strong> ' + esc(d.usecase) + '</p>' +
      '<div class="hf-card-tags">' + pills + '</div>' +
      '<div class="hf-card-links">' + hfLink +
        (d.access === "credentialed" ? '<span class="card-link-note">Requires PhysioNet credentials</span>' : '') +
      '</div>' +
    '</article>';
  }

  // ── Filter helpers ───────────────────────────────────────────────────────────
  function filteredModels() {
    var q = state.q.toLowerCase();
    var items = (data.health_models || []).filter(function (m) {
      if (state.medOnly && !m.medical_tuned) return false;
      if (state.licType !== "all" && m.license_type !== state.licType) return false;
      if (state.paramsSize !== "all") {
        var range = PARAMS_RANGES[state.paramsSize];
        if (range && !range.test(m)) return false;
      }
      if (state.tags.length) {
        var mt = m.tags || [];
        if (!state.tags.every(function (t) { return mt.indexOf(t) !== -1; })) return false;
      }
      if (q) {
        var blob = (m.name + " " + m.developer + " " + m.usecase + " " + m.strength + " " + (m.tags || []).join(" ")).toLowerCase();
        if (blob.indexOf(q) === -1) return false;
      }
      return true;
    });
    return items;
  }

  function filteredDatasets() {
    var q = state.q.toLowerCase();
    var items = (data.health_datasets || []).filter(function (d) {
      if (state.access !== "all" && d.access !== state.access) return false;
      if (state.tags.length) {
        var typeLabel = DATASET_TYPE_LABELS[d.type] || d.type;
        if (!state.tags.some(function (t) { return typeLabel === t || d.type === t; })) return false;
      }
      if (q) {
        var blob = (d.name + " " + d.type + " " + d.description + " " + d.usecase + " " + (d.tags || []).join(" ")).toLowerCase();
        if (blob.indexOf(q) === -1) return false;
      }
      return true;
    });
    return items;
  }

  // ── Render grid ──────────────────────────────────────────────────────────────
  function renderGrid() {
    var grid = $("catalog-grid");
    var countEl = $("result-count");
    if (!grid) return;

    var items, cards;
    if (PAGE === "models") {
      items = filteredModels();
      cards = items.map(modelCard);
    } else {
      items = filteredDatasets();
      cards = items.map(datasetCard);
    }

    if (countEl) {
      var total = PAGE === "models" ? (data.health_models || []).length : (data.health_datasets || []).length;
      countEl.textContent = items.length + " of " + total + " " + (PAGE === "models" ? "models" : "datasets");
    }

    if (!cards.length) {
      grid.innerHTML = '<div class="catalog-empty-state"><p>No results match your filters.</p><button id="clear-filters">Clear all filters</button></div>';
      var cb = $("clear-filters");
      if (cb) cb.addEventListener("click", clearAll);
      return;
    }

    grid.innerHTML = cards.join("");
  }

  function clearAll() {
    state.q = ""; state.tags = []; state.medOnly = false;
    state.licType = "all"; state.paramsSize = "all"; state.access = "all";
    var qi = $("search-input");
    if (qi) qi.value = "";
    bindSidebarState();
    renderGrid();
  }

  // ── Sidebar state sync ───────────────────────────────────────────────────────
  function bindSidebarState() {
    // Checkboxes
    ["med-only"].forEach(function (id) {
      var el = $(id);
      if (el) el.checked = state.medOnly;
    });
    // Selects
    ["lic-type", "params-size", "access-filter"].forEach(function (id) {
      var el = $(id);
      if (!el) return;
      if (id === "lic-type") el.value = state.licType;
      if (id === "params-size") el.value = state.paramsSize;
      if (id === "access-filter") el.value = state.access;
    });
    // Tag buttons
    document.querySelectorAll(".sidebar-tag").forEach(function (btn) {
      var t = btn.dataset.tag;
      btn.classList.toggle("active", state.tags.indexOf(t) !== -1);
    });
  }

  // ── Build sidebar tag pills ──────────────────────────────────────────────────
  function buildTagPills() {
    var container = $("tag-filters");
    if (!container) return;

    var allTags;
    if (PAGE === "models") {
      var seen = {};
      (data.health_models || []).forEach(function (m) {
        (m.tags || []).forEach(function (t) { seen[t] = (seen[t] || 0) + 1; });
      });
      allTags = Object.keys(seen).sort(function (a, b) { return seen[b] - seen[a]; });
    } else {
      var types = {};
      (data.health_datasets || []).forEach(function (d) {
        var label = DATASET_TYPE_LABELS[d.type] || d.type;
        types[label] = (types[label] || 0) + 1;
      });
      allTags = Object.keys(types).sort(function (a, b) { return types[b] - types[a]; });
    }

    container.innerHTML = allTags.map(function (t) {
      var label = PAGE === "models" ? (TAG_LABELS[t] || t) : t;
      return '<button class="sidebar-tag" data-tag="' + esc(t) + '">' + esc(label) + '</button>';
    }).join("");

    container.addEventListener("click", function (e) {
      var btn = e.target.closest(".sidebar-tag");
      if (!btn) return;
      var t = btn.dataset.tag;
      var idx = state.tags.indexOf(t);
      if (idx === -1) state.tags.push(t);
      else state.tags.splice(idx, 1);
      btn.classList.toggle("active", state.tags.indexOf(t) !== -1);
      renderGrid();
    });
  }

  // ── Bind controls ────────────────────────────────────────────────────────────
  function bindControls() {
    var qi = $("search-input");
    if (qi) qi.addEventListener("input", function (e) { state.q = e.target.value; renderGrid(); });

    var med = $("med-only");
    if (med) med.addEventListener("change", function (e) { state.medOnly = e.target.checked; renderGrid(); });

    var lic = $("lic-type");
    if (lic) lic.addEventListener("change", function (e) { state.licType = e.target.value; renderGrid(); });

    var ps = $("params-size");
    if (ps) ps.addEventListener("change", function (e) { state.paramsSize = e.target.value; renderGrid(); });

    var ac = $("access-filter");
    if (ac) ac.addEventListener("change", function (e) { state.access = e.target.value; renderGrid(); });

    var clr = $("clear-btn");
    if (clr) clr.addEventListener("click", clearAll);
  }

  // ── Boot ─────────────────────────────────────────────────────────────────────
  fetch("data.json")
    .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then(function (json) {
      data = json;
      buildTagPills();
      bindControls();
      renderGrid();
    })
    .catch(function (err) {
      var g = $("catalog-grid");
      if (g) g.innerHTML = '<p class="catalog-empty-state">Could not load data: ' + esc(err.message) + '</p>';
    });
})();
