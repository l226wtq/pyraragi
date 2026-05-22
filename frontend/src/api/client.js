const jsonHeaders = { "Content-Type": "application/json" };

export async function fetchArchives(params) {
  const query = new URLSearchParams(params);
  return fetchJson(`/api/archives?${query.toString()}`);
}

export async function fetchArchive(id) {
  return fetchJson(`/api/archives/${id}`);
}

export async function fetchPages(id) {
  return fetchJson(`/api/archives/${id}/pages`);
}

export async function scanLibrary() {
  return fetchJson("/api/library/scan", { method: "POST", headers: jsonHeaders });
}

export async function fetchJobs() {
  return fetchJson("/api/jobs");
}

export async function startJob(jobType) {
  return fetchJson(`/api/jobs/${jobType}`, { method: "POST", headers: jsonHeaders });
}

export async function stopJob(jobId) {
  return fetchJson(`/api/jobs/${jobId}/stop`, { method: "POST", headers: jsonHeaders });
}

export async function fetchDuplicateGroups() {
  return fetchJson("/api/jobs/duplicates/groups");
}

export async function uploadArchive(formData) {
  return fetchJson("/api/archives", { method: "POST", body: formData });
}

export async function fetchConversionJobs() {
  return fetchJson("/api/conversions?limit=50");
}

export async function fetchConversionTools() {
  return fetchJson("/api/conversions/tools");
}

export async function createConversionJob(payload) {
  return fetchJson("/api/conversions", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
}

export async function uploadConversionArchive(formData) {
  return fetchJson("/api/conversions/upload", { method: "POST", body: formData });
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    throw new Error(payload?.detail || payload?.error || `Request failed: ${response.status}`);
  }
  return payload;
}
