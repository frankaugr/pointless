import { normalise } from "./match.js";

export function flattenRounds(payload) {
  const rounds = [];
  for (const episode of payload.episodes || []) {
    for (const round of episode.rounds || []) {
      rounds.push({
        episodeId: episode.episode_id,
        episodeLabel: episode.episode_label,
        sourceUrl: episode.source_url,
        category: round.category_text,
        confidence: round.category_confidence,
        answers: roundAnswers(round),
      });
    }
  }
  return rounds;
}

export function roundAnswers(round) {
  return (round.facts || []).map((fact, idx) => ({
    id: `${normalise(fact.answer).replace(/ /g, "-")}-${idx}`,
    name: fact.answer,
    aliases: [],
    isPointless: Boolean(fact.is_pointless),
    obscurity: { pointless_score: fact.score, confidence: "high" },
  }));
}

export function pickRound(rounds, exceptKey = "") {
  if (!rounds.length) return null;
  const pool = rounds.length > 1
    ? rounds.filter((round) => roundKey(round) !== exceptKey)
    : rounds;
  return pool[Math.floor(Math.random() * pool.length)];
}

export function roundKey(round) {
  return `${round.episodeId}:${round.category}`;
}

export function bestFound(round, foundIds) {
  const found = round.answers.filter((answer) => foundIds.has(answer.id));
  if (!found.length) return null;
  return found.reduce((best, answer) =>
    answer.obscurity.pointless_score < best.obscurity.pointless_score ? answer : best,
  );
}
