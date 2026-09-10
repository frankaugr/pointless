import { displayFields } from "./data.js";
import { normalise } from "./match.js";

export const DAY = 86400000;
export const MEMORY_KEY = "pointless-memory-v1";

export function categoryCards(category) {
  return category.answers.map(answer => ({
    id: `${category.slug}:${answer.id}`,
    deck: category.slug,
    group: category.name,
    name: answer.name,
    aliases: answer.aliases || [],
    clue: displayFields(category, answer).map(f => `${f.label}: ${f.value}`).join(" · "),
    source: answer.wiki || category.sources?.[0]?.url || "",
    sourceLabel: "Read more",
    scope: category.description,
  })).filter(card => card.clue);
}

// Self-assessed recall: a miss returns shortly; successful recalls space out.
export function schedule(previous = {}, grade, now = Date.now()) {
  if (!["again", "hard", "good"].includes(grade)) throw new Error("Unknown rating");
  const interval = grade === "again" ? 0 : grade === "hard" ? 1
    : Math.min(180, Math.max(3, Math.round((previous.interval || 0) * 2)));
  return {
    ...previous, interval, due: now + (interval ? interval * DAY : 600000),
    reviews: (previous.reviews || 0) + 1,
    lapses: (previous.lapses || 0) + (grade === "again" ? 1 : 0),
    lastGrade: grade, lastReviewed: now,
  };
}

export function makeQueue(cards, progress, mode = "due", limit = 10, now = Date.now(), random = Math.random) {
  const shuffled = cards.map(card => ({card, tie: random()}));
  return shuffled.filter(({card}) => {
    const p = progress[card.id];
    if (mode === "weak") return p?.lastGrade === "again" || p?.lastGrade === "hard";
    if (mode === "all") return true;
    return !p?.reviews || p.due <= now;
  }).sort((a, b) => {
    if (mode !== "due") return a.tie - b.tie;
    const pa = progress[a.card.id], pb = progress[b.card.id];
    // Overdue cards come before unseen cards.
    return (pa?.reviews ? 0 : 1) - (pb?.reviews ? 0 : 1)
      || (pa?.reviews && pb?.reviews ? pa.due - pb.due : 0) || a.tie - b.tie;
  }).slice(0, limit).map(({card}) => card);
}

export function counts(cards, progress, now = Date.now()) {
  return cards.reduce((out, card) => {
    const p = progress[card.id];
    if (!p?.reviews) out.new++;
    else {
      if (p.due <= now) out.due++;
      if (p.interval >= 6) out.established++;
    }
    return out;
  }, {new: 0, due: 0, established: 0});
}

export function accepts(input, card, cards) {
  const key = normalise(input);
  if (!key) return false;
  const names = c => [c.name, ...(c.aliases || [])].map(normalise);
  if (names(card).includes(key)) return true;
  // Only accept a surname when it identifies one person in this deck.
  const matches = cards.filter(c => names(c).some(n => n.split(" ").at(-1) === key));
  return matches.length === 1 && matches[0].id === card.id;
}

export function validateProgress(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid progress file");
  const clean = {};
  for (const [key, row] of Object.entries(value)) {
    if (!key.includes(":") || !row || typeof row !== "object" || Array.isArray(row)) throw new Error("Invalid card record");
    const p = {};
    if (typeof row.note === "string") p.note = row.note.slice(0, 1000);
    if (row.reviews !== undefined) {
      for (const field of ["reviews", "lapses", "due", "interval", "lastReviewed"]) {
        if (!Number.isFinite(row[field]) || row[field] < 0) throw new Error("Invalid review history");
        p[field] = row[field];
      }
      if (!["again", "hard", "good"].includes(row.lastGrade)) throw new Error("Invalid rating");
      p.lastGrade = row.lastGrade;
    }
    clean[key] = p;
  }
  return clean;
}
