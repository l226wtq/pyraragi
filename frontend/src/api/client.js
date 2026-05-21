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

export async function uploadArchive(formData) {
  return fetchJson("/api/archives", { method: "POST", body: formData });
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
