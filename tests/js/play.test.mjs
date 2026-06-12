import assert from "node:assert/strict";
import test from "node:test";

import { bestFound, flattenRounds, pickRound, roundAnswers, roundKey } from "../../docs/js/play.js";

const payload = {
  episodes: [
    {
      episode_id: "s34e01",
      episode_label: "Series 34 Episode 1",
      source_url: "https://www.bbc.co.uk/programmes/m002jwx4",
      rounds: [
        {
          category_text: "Teams at Euro 2024",
          category_confidence: "high",
          facts: [
            { answer: "Italy", score: 57, is_pointless: false },
            { answer: "Czechia", score: 3, is_pointless: false },
            { answer: "Georgia", score: 0, is_pointless: true },
          ],
        },
      ],
    },
  ],
};

test("flattenRounds maps episodes to playable rounds", () => {
  const rounds = flattenRounds(payload);
  assert.equal(rounds.length, 1);
  assert.equal(rounds[0].episodeLabel, "Series 34 Episode 1");
  assert.equal(rounds[0].category, "Teams at Euro 2024");
  assert.equal(rounds[0].answers.length, 3);
});

test("roundAnswers produces match-index compatible answers", () => {
  const answers = roundAnswers(payload.episodes[0].rounds[0]);
  assert.equal(answers[0].name, "Italy");
  assert.equal(answers[0].obscurity.pointless_score, 57);
  assert.equal(answers[2].isPointless, true);
  assert.equal(new Set(answers.map((a) => a.id)).size, 3);
});

test("bestFound returns the lowest scoring found answer", () => {
  const [round] = flattenRounds(payload);
  assert.equal(bestFound(round, new Set()), null);
  const found = new Set([round.answers[0].id, round.answers[1].id]);
  assert.equal(bestFound(round, found).name, "Czechia");
});

test("pickRound avoids the previous round when possible", () => {
  const rounds = [
    { episodeId: "a", category: "one", answers: [] },
    { episodeId: "b", category: "two", answers: [] },
  ];
  for (let i = 0; i < 20; i += 1) {
    const picked = pickRound(rounds, roundKey(rounds[0]));
    assert.equal(roundKey(picked), roundKey(rounds[1]));
  }
  assert.notEqual(pickRound([rounds[0]], roundKey(rounds[0])), null);
});
