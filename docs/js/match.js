const STOPWORDS = new Set([
  "the", "of", "and", "de", "la", "le", "el", "von", "van", "der", "den",
  "sir", "lord", "lady", "earl", "viscount", "duke", "baron", "marquess",
  "king", "queen", "president", "prime", "minister", "city", "saint", "st",
  "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th",
  "11th", "12th", "13th", "14th", "15th", "16th", "17th", "18th", "19th", "20th",
]);

const UNSAFE_SINGLE_TOKENS = new Set([
  "al", "anne", "charles", "david", "edward", "george", "henry", "james", "john",
  "mary", "richard", "robert", "thomas", "william",
]);

export function normalise(value) {
  return String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9 ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function addKey(target, value) {
  const key = normalise(value);
  if (key) target.add(key);
}

function meaningfulTokens(value) {
  return normalise(value)
    .split(" ")
    .filter((token) => token.length >= 3 && !STOPWORDS.has(token));
}

export function buildAnswerIndex(answers) {
  const strongKeysById = new Map();
  const weakKeys = new Map();

  for (const answer of answers) {
    const strong = new Set();
    addKey(strong, answer.name);
    addKey(strong, answer.name.split(",")[0]);
    for (const alias of answer.aliases || []) {
      addKey(strong, alias);
    }
    strongKeysById.set(answer.id, strong);

    const weak = new Set();
    for (const phrase of [answer.name, answer.name.split(",")[0], ...(answer.aliases || [])]) {
      const tokens = meaningfulTokens(phrase);
      const last = tokens[tokens.length - 1];
      if (last && !UNSAFE_SINGLE_TOKENS.has(last)) {
        weak.add(last);
      }
      if (tokens.length >= 2) {
        weak.add(tokens.slice(-2).join(" "));
      }
    }
    for (const key of weak) {
      if (!weakKeys.has(key)) weakKeys.set(key, []);
      weakKeys.get(key).push(answer.id);
    }
  }

  const keyMap = new Map();
  for (const answer of answers) {
    for (const key of strongKeysById.get(answer.id)) {
      if (!keyMap.has(key)) keyMap.set(key, []);
      keyMap.get(key).push(answer);
    }
  }

  for (const [key, ids] of weakKeys) {
    const uniqueIds = [...new Set(ids)];
    if (uniqueIds.length !== 1) continue;
    const answer = answers.find((item) => item.id === uniqueIds[0]);
    if (!answer) continue;
    if (!keyMap.has(key)) keyMap.set(key, []);
    keyMap.get(key).push(answer);
  }

  for (const [key, matches] of keyMap) {
    const seen = new Set();
    keyMap.set(
      key,
      matches.filter((answer) => {
        if (seen.has(answer.id)) return false;
        seen.add(answer.id);
        return true;
      }),
    );
  }

  return { answers, keyMap };
}

export function findMatches(input, index, foundIds = new Set()) {
  const query = normalise(input);
  if (!query) return { status: "empty", matches: [] };

  let matches = index.keyMap.get(query) || [];
  if (matches.length === 0 && query.length >= 4 && !UNSAFE_SINGLE_TOKENS.has(query)) {
    matches = fuzzyMatches(query, index);
  }

  if (matches.length === 0) return { status: "none", matches: [] };

  const active = matches.filter((answer) => !foundIds.has(answer.id));
  if (active.length === 0) return { status: "duplicate", matches };
  if (active.length > 1) return { status: "ambiguous", matches: active };
  return { status: "match", matches: active };
}

function fuzzyMatches(query, index) {
  const out = [];
  const seen = new Set();
  for (const [key, matches] of index.keyMap) {
    if (key.length < 4) continue;
    const closeLength = Math.abs(key.length - query.length) <= 3;
    if (!closeLength) continue;
    if (!key.includes(query) && !query.includes(key)) continue;
    for (const answer of matches) {
      if (seen.has(answer.id)) continue;
      seen.add(answer.id);
      out.push(answer);
    }
  }
  return out;
}
