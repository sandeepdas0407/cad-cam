const searchInput = document.getElementById("search-input");
const searchBtn = document.getElementById("search-btn");
const searchType = document.getElementById("search-type");
const resultsEl = document.getElementById("results");
const reindexBtn = document.getElementById("reindex-btn");
const indexStatusEl = document.getElementById("index-status");
const docTypeCheckboxes = document.querySelectorAll(".doc-type-filter");

let debounceTimer = null;

function selectedDocTypes() {
  const checked = Array.from(docTypeCheckboxes).filter((c) => c.checked).map((c) => c.value);
  if (checked.length === 0 || checked.length === docTypeCheckboxes.length) return "all";
  return checked[0]; // API supports one doc_type filter value at a time
}

async function runSearch() {
  const q = searchInput.value.trim();
  if (!q) {
    resultsEl.innerHTML = "";
    return;
  }
  const params = new URLSearchParams({
    q,
    type: searchType.value,
    doc_type: selectedDocTypes(),
    limit: "20",
  });
  const res = await fetch(`/api/search?${params.toString()}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Search failed." }));
    resultsEl.innerHTML = `<li class="empty-state">${escapeHtml(err.detail || "Search failed.")}</li>`;
    return;
  }
  const data = await res.json();
  renderResults(data.results, data.warning);
}

function renderResults(results, warning) {
  const warningHtml = warning ? `<li class="empty-state">${escapeHtml(warning)}</li>` : "";
  if (!results || results.length === 0) {
    resultsEl.innerHTML = warningHtml || '<li class="empty-state">No results.</li>';
    return;
  }
  resultsEl.innerHTML = warningHtml + results
    .map((r) => {
      const loc = r.page_number
        ? `Page ${r.page_number}`
        : r.section_heading
        ? r.section_heading
        : "";
      const ocrTag = r.source === "ocr" || r.source === "mixed" ? '<span class="ocr-tag">OCR</span>' : "";
      const href = r.page_number ? `/api/file/${r.doc_id}#page=${r.page_number}` : `/api/file/${r.doc_id}`;
      return `
        <li class="result-item">
          <a class="result-title" href="${href}" target="_blank" rel="noopener">${escapeHtml(r.filename)}</a>
          <div class="result-meta">${r.doc_type.toUpperCase()} ${loc ? "&middot; " + escapeHtml(loc) : ""}${ocrTag}</div>
          <div class="result-snippet">${r.snippet_html}</div>
        </li>`;
    })
    .join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

searchInput.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(runSearch, 250);
});
searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    clearTimeout(debounceTimer);
    runSearch();
  }
});
searchBtn.addEventListener("click", () => {
  clearTimeout(debounceTimer);
  runSearch();
});
searchType.addEventListener("change", runSearch);
docTypeCheckboxes.forEach((c) => c.addEventListener("change", runSearch));

reindexBtn.addEventListener("click", async () => {
  await fetch("/api/reindex", { method: "POST" });
  pollStatus();
});

async function pollStatus() {
  const res = await fetch("/api/index/status");
  const data = await res.json();
  if (data.status === "running") {
    indexStatusEl.textContent = `Indexing ${data.files_processed}/${data.files_total}...`;
    setTimeout(pollStatus, 800);
  } else if (data.status === "done" || data.status === "done_with_errors") {
    indexStatusEl.textContent = `Last indexed: ${data.last_run_at || ""} (${data.files_processed} files${
      data.errors.length ? ", " + data.errors.length + " errors" : ""
    })`;
  } else {
    indexStatusEl.textContent = "Idle";
  }
}

pollStatus();
