import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";
import {DAY, schedule, makeQueue, counts, accepts, categoryCards, validateProgress} from "../../docs/js/memory.js";

const now = 1800000000000;
const cards = [{id:"test:a", name:"George Bush", aliases:[]}, {id:"test:b", name:"George W. Bush", aliases:[]}, {id:"test:c", name:"Garbiñe Muguruza", aliases:[]}];

test("misses, effort and success schedule reviews without losing private cues", () => {
  const miss = schedule({note:"My cue"}, "again", now);
  assert.equal(miss.due, now + 600000);
  assert.equal(miss.lapses, 1);
  assert.equal(miss.note, "My cue");
  const hard = schedule(miss, "hard", now);
  assert.equal(hard.due, now + DAY);
  const good = schedule(hard, "good", now);
  assert.equal(good.due, now + 3 * DAY);
  assert.equal(schedule(good, "good", now).interval, 6);
  assert.equal(schedule({interval:180}, "good", now).interval, 180);
  assert.equal(schedule(good, "again", now).interval, 0);
  assert.throws(() => schedule({}, "bogus", now));
});

test("due queue puts overdue reviews first and excludes future cards", () => {
  const progress = {"test:a":schedule({}, "good", now), "test:b":schedule({}, "again", now - DAY)};
  assert.deepEqual(makeQueue(cards, progress, "due", 10, now).map(c => c.id), ["test:b", "test:c"]);
  assert.equal(makeQueue(cards, progress, "due", 1, now)[0].id, "test:b");
  assert.equal(makeQueue(cards, progress, "all", 10, now).length, 3);
  assert.deepEqual(makeQueue(cards, progress, "weak", 10, now).map(c => c.id), ["test:b"]);
});

test("a cue alone does not make a card reviewed, and due boundary is inclusive", () => {
  const progress = {"test:a":{note:"Bush"}, "test:b":{...schedule({}, "good", now), due:now, interval:6}};
  assert.deepEqual(counts(cards, progress, now), {new:2, due:1, established:1});
  assert.equal(makeQueue(cards, progress, "due", 10, now).length, 3);
});

test("recall accepts accents and unique surnames but rejects ambiguous surnames and fragments", () => {
  assert.equal(accepts("Muguruza", cards[2], cards), true);
  assert.equal(accepts("Garbine Muguruza", cards[2], cards), true);
  assert.equal(accepts("Bush", cards[0], cards), false);
  assert.equal(accepts("George W Bush", cards[1], cards), true);
  assert.equal(accepts("Mugur", cards[2], cards), false);
  assert.equal(accepts("", cards[0], cards), false);
});

test("political decks preserve full coverage and stable IDs without score filtering", async () => {
  for (const [slug, count] of [["uk-prime-ministers",58], ["us-presidents",45]]) {
    const category = JSON.parse(await readFile(new URL(`../../docs/data/${slug}.json`, import.meta.url)));
    const result = categoryCards(category);
    assert.equal(result.length, count);
    assert.equal(new Set(result.map(c => c.id)).size, count);
    assert(result.every(c => c.clue.includes("First Served:") && c.clue.includes("Party:")));
    assert(result.every(c => c.id.startsWith(slug + ":")));
  }
});

test("backup validation rejects malformed records atomically", () => {
  const valid = {"test:a":schedule({note:"Personal cue"}, "good", now)};
  assert.deepEqual(validateProgress(JSON.parse(JSON.stringify(valid))), valid);
  assert.throws(() => validateProgress([]));
  assert.throws(() => validateProgress({"test:a":{reviews:1, due:"tomorrow"}}));
  assert.throws(() => validateProgress({...valid, "test:b":null}));
  assert.equal(validateProgress({"test:a":{note:"a".repeat(2000)}})["test:a"].note.length, 1000);
});

test("offline shell caches the new modules and every local core asset exists", async () => {
  const sw = await readFile(new URL("../../docs/sw.js", import.meta.url), "utf8");
  const core = sw.match(/const CORE = \[([\s\S]*?)\];/)[1];
  assert(core.includes('"js/memory.js"') && core.includes('"js/memory-ui.js"'));
  for (const [, path] of core.matchAll(/"([^"]+)"/g)) {
    if (path !== "./") await readFile(new URL(`../../docs/${path}`, import.meta.url));
  }
});
