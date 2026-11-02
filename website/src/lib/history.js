const KEY = "corvus.predictions";

// ponytail: session-local history until GET /patients/me/predictions ships (phase 8-03).
// Entries are the real /v2/predict responses, so nothing here is invented.
export function addPrediction(entry) {
  const next = [{ ...entry, at: new Date().toISOString() }, ...getPredictions()].slice(0, 50);
  localStorage.setItem(KEY, JSON.stringify(next));
  return next;
}

export function getPredictions() {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(raw) ? raw : [];
  } catch {
    return [];
  }
}

export function clearPredictions() {
  localStorage.removeItem(KEY);
}

export function formatStamp(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
