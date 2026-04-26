export async function loadCatalog() {
  const data = await fetchJson("data/categories.json");
  return data.categories || [];
}

export async function loadCategory(slug) {
  return fetchJson(`data/${slug}.json`);
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`);
  }
  return response.json();
}

export function sortAnswers(answers, sortMode) {
  const copy = [...answers];
  if (sortMode === "name") {
    copy.sort((a, b) => a.name.localeCompare(b.name));
  } else if (sortMode === "familiar") {
    copy.sort((a, b) => pointlessScore(b) - pointlessScore(a) || a.name.localeCompare(b.name));
  } else {
    copy.sort((a, b) => pointlessScore(a) - pointlessScore(b) || a.name.localeCompare(b.name));
  }
  return copy;
}

export function fieldLabel(field) {
  return String(field)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

export function displayFields(category, answer) {
  return (category.display_fields || [])
    .map((field) => {
      const value = answer.attrs?.[field];
      return value == null || value === "" ? null : { field, label: fieldLabel(field), value };
    })
    .filter(Boolean);
}

export function rareCount(answers, threshold = 0.66) {
  return answers.filter((answer) => (answer.obscurity?.score ?? 0) >= threshold).length;
}

export function pointlessScore(answer) {
  const exported = answer.obscurity?.pointless_score;
  if (typeof exported === "number") {
    return Math.max(0, Math.min(100, Math.round(exported)));
  }
  const observed = answer.obscurity?.components?.pointless_average_score;
  if (typeof observed === "number") {
    return Math.max(0, Math.min(100, Math.round(observed)));
  }
  return Math.max(0, Math.min(100, Math.round((1 - (answer.obscurity?.score ?? 0)) * 100)));
}

export function lowScoreCount(answers, maxScore = 50) {
  return answers.filter((answer) => pointlessScore(answer) <= maxScore).length;
}

export function scoreBand(score) {
  if (score === 0) return "pointless target";
  if (score <= 10) return "excellent";
  if (score <= 30) return "strong low scorer";
  if (score <= 50) return "playable";
  return "high scorer";
}
