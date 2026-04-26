import { normalise } from "./match.js";

const VOWELS = new Set(["a", "e", "i", "o", "u"]);

export function buildQuestionCandidates(category, options = {}) {
  const minAnswers = options.minAnswers ?? 3;
  const maxAnswers = options.maxAnswers ?? 25;
  const rareThreshold = options.rareThreshold ?? 0.55;
  const candidates = [];

  for (const template of category.question_templates || []) {
    for (const expanded of expandTemplate(category.answers, template)) {
      const answers = category.answers.filter((answer) => answerMatchesTemplate(answer, expanded));
      const rare = answers.filter((answer) => (answer.obscurity?.score ?? 0) >= rareThreshold).length;
      candidates.push({
        id: expanded.id,
        prompt: renderPrompt(category, expanded),
        template: expanded,
        answers,
        answerCount: answers.length,
        rareCount: rare,
        eligible: answers.length >= minAnswers && answers.length <= maxAnswers && rare > 0,
      });
    }
  }

  return candidates.sort((a, b) => {
    if (a.eligible !== b.eligible) return a.eligible ? -1 : 1;
    return a.answerCount - b.answerCount || a.prompt.localeCompare(b.prompt);
  });
}

export function pickQuestion(category, options = {}) {
  const candidates = buildQuestionCandidates(category, options).filter((candidate) => candidate.eligible);
  if (candidates.length === 0) return null;
  const index = Math.floor(Math.random() * candidates.length);
  return candidates[index];
}

export function expandTemplate(answers, template) {
  if (template.kind !== "attr_equals_dynamic") {
    return [template];
  }
  const values = [...new Set(answers.map((answer) => answer.attrs?.[template.attr]).filter(Boolean))];
  return values.map((value) => ({
    ...template,
    id: `${template.id}-${slugValue(value)}`,
    kind: "attr_equals",
    value,
  }));
}

export function answerMatchesTemplate(answer, template) {
  if (template.kind === "starts_with_consonant") {
    const first = firstLetter(valueFor(answer, template));
    return Boolean(first && !VOWELS.has(first));
  }
  if (template.kind === "contains_any_letters") {
    const text = normalise(valueFor(answer, template)).replace(/ /g, "");
    const letters = [...new Set(String(template.letters || "").toLowerCase().replace(/[^a-z]/g, ""))];
    return letters.some((letter) => text.includes(letter));
  }
  if (template.kind === "name_length_at_most") {
    return compact(valueFor(answer, template)).length <= Number(template.max);
  }
  if (template.kind === "first_vowel") {
    const firstVowel = [...compact(valueFor(answer, template))].find((letter) => VOWELS.has(letter));
    return firstVowel === String(template.value).toLowerCase();
  }
  if (template.kind === "number_range") {
    const value = Number(answer.attrs?.[template.attr]);
    return Number.isFinite(value) && value >= Number(template.min) && value <= Number(template.max);
  }
  if (template.kind === "text_length") {
    return String(answer.attrs?.[template.attr] || "").length === Number(template.value);
  }
  if (template.kind === "attr_equals") {
    return String(answer.attrs?.[template.attr]) === String(template.value);
  }
  if (template.kind === "same_initial") {
    const left = firstLetter(valueFor(answer, template));
    const right = firstLetter(answer.attrs?.[template.attr]);
    return Boolean(left && right && left === right);
  }
  return false;
}

function valueFor(answer, template) {
  if (template.field === "name") return answer.name;
  if (template.attr) return answer.attrs?.[template.attr];
  return answer.name;
}

function renderPrompt(category, template) {
  return String(template.prompt || "{category}")
    .replaceAll("{category}", category.name)
    .replaceAll("{value}", String(template.value ?? ""));
}

function firstLetter(value) {
  return compact(value).slice(0, 1);
}

function compact(value) {
  return normalise(value).replace(/[^a-z0-9]/g, "");
}

function slugValue(value) {
  return normalise(value).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
