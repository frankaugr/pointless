import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { lowScoreCount, pointlessScore, sortAnswers } from "../../docs/js/data.js";
import { buildAnswerIndex, findMatches } from "../../docs/js/match.js";
import { answerMatchesTemplate, buildQuestionCandidates } from "../../docs/js/questions.js";

async function loadCategory(slug) {
  const raw = await readFile(new URL(`../../docs/data/${slug}.json`, import.meta.url), "utf8");
  return JSON.parse(raw);
}

test("element consonant example returns only consonant-starting elements", async () => {
  const category = await loadCategory("chemical-elements");
  const template = category.question_templates.find((item) => item.id === "elements-consonant");
  const matches = category.answers.filter((answer) => answerMatchesTemplate(answer, template));
  assert(matches.some((answer) => answer.name === "Hydrogen"));
  assert(!matches.some((answer) => answer.name === "Oxygen"));
  assert(matches.every((answer) => answer.attrs.starts_with_consonant));
});

test("state-capital STATE-letter example returns matching subset", async () => {
  const category = await loadCategory("us-state-capitals");
  const template = category.question_templates.find((item) => item.id === "state-capitals-containing-state");
  const matches = category.answers.filter((answer) => answerMatchesTemplate(answer, template));
  assert(matches.some((answer) => answer.name === "Austin"));
  assert(matches.every((answer) => /[state]/i.test(answer.name)));
});

test("random revision candidates stay within useful answer bounds", async () => {
  const index = JSON.parse(await readFile(new URL("../../docs/data/categories.json", import.meta.url), "utf8"));
  for (const summary of index.categories) {
    const category = await loadCategory(summary.slug);
    const candidates = buildQuestionCandidates(category).filter((candidate) => candidate.eligible);
    assert(candidates.length > 0, `${summary.slug} has no eligible questions`);
    assert(candidates.every((candidate) => candidate.answerCount >= 3 && candidate.answerCount <= 25));
  }
});

test("answer matching supports explicit ambiguity and safe surnames", async () => {
  const cities = await loadCategory("uk-cities");
  const cityIndex = buildAnswerIndex(cities.answers);
  assert.equal(findMatches("Bangor", cityIndex).status, "ambiguous");

  const pms = await loadCategory("uk-prime-ministers");
  const pmIndex = buildAnswerIndex(pms.answers);
  const thatcher = findMatches("Thatcher", pmIndex);
  assert.equal(thatcher.status, "match");
  assert.equal(thatcher.matches[0].name, "Margaret Thatcher");
  assert.equal(findMatches("John", pmIndex).status, "none");
});

test("display score uses Pointless semantics where 0 is best and 100 is worst", async () => {
  const pms = await loadCategory("uk-prime-ministers");
  const byName = new Map(pms.answers.map((answer) => [answer.name, answer]));
  assert.equal(pointlessScore(byName.get("Henry Pelham")), 0);
  assert.equal(pointlessScore(byName.get("Tony Blair")), 86);
  assert(pointlessScore(byName.get("Tony Blair")) > pointlessScore(byName.get("Henry Pelham")));
});

test("learn default can hide scores above 50", async () => {
  const pms = await loadCategory("uk-prime-ministers");
  const visibleByDefault = pms.answers.filter((answer) => pointlessScore(answer) <= 50);
  assert.equal(visibleByDefault.length, lowScoreCount(pms.answers));
  assert(visibleByDefault.length < pms.answers.length);
  assert(visibleByDefault.every((answer) => pointlessScore(answer) <= 50));
  assert(sortAnswers(visibleByDefault, "obscurity")[0].name !== "Tony Blair");
});
