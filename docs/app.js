const STOPWORDS = new Set([
  "the", "of", "and", "de", "la", "le", "el", "von", "van", "der", "den",
  "sir", "lord", "lady", "earl", "viscount", "duke", "baron", "marquess",
  "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th",
]);

function normalise(s) {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9 ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function acceptKeys(canonical) {
  const keys = new Set();
  const norm = normalise(canonical);
  if (norm) keys.add(norm);

  const beforeComma = canonical.split(",")[0];
  const beforeNorm = normalise(beforeComma);
  if (beforeNorm) keys.add(beforeNorm);

  for (const segment of [canonical, beforeComma]) {
    const tokens = normalise(segment)
      .split(" ")
      .filter((t) => t.length >= 3 && !STOPWORDS.has(t));
    for (const t of tokens) keys.add(t);
    if (tokens.length >= 2) {
      keys.add(tokens.slice(0, 2).join(" "));
      keys.add(tokens.slice(-2).join(" "));
    }
  }

  return keys;
}

const state = {
  catalog: [],
  current: null,
  answers: [],
  found: new Set(),
};

const $ = (id) => document.getElementById(id);

async function loadCatalog() {
  const res = await fetch("data/categories.json", { cache: "no-cache" });
  if (!res.ok) throw new Error(`failed to load catalog: ${res.status}`);
  const data = await res.json();
  state.catalog = data.categories || [];

  const select = $("category");
  select.innerHTML = "";
  for (const cat of state.catalog) {
    const opt = document.createElement("option");
    opt.value = cat.slug;
    opt.textContent = `${cat.name} (${cat.n_answers})`;
    select.appendChild(opt);
  }
  updatePickerMeta();
  select.addEventListener("change", updatePickerMeta);
}

function updatePickerMeta() {
  const slug = $("category").value;
  const cat = state.catalog.find((c) => c.slug === slug);
  $("picker-meta").textContent = cat ? cat.description : "";
}

async function startQuiz(slug) {
  const res = await fetch(`data/${slug}.json`, { cache: "no-cache" });
  if (!res.ok) throw new Error(`failed to load category: ${res.status}`);
  const data = await res.json();

  state.current = data;
  state.answers = data.answers.map((a, i) => ({
    ...a,
    id: i,
    keys: acceptKeys(a.name),
  }));
  state.found = new Set();

  $("picker").hidden = true;
  $("quiz").hidden = false;
  $("missed-section").hidden = true;
  $("quiz-title").textContent = data.name;
  $("found-list").innerHTML = "";
  $("missed-list").innerHTML = "";
  $("answer-input").value = "";
  $("answer-input").focus();
  updateProgress();
  setFeedback("");
}

function updateProgress() {
  const total = state.answers.length;
  const got = state.found.size;
  $("found-count").textContent = String(got);
  $("quiz-progress").textContent = `${got} / ${total} answers found`;
}

function setFeedback(text, kind = "") {
  const el = $("feedback");
  el.textContent = text;
  el.className = `feedback ${kind}`;
}

function findMatch(input) {
  const q = normalise(input);
  if (!q) return null;
  for (const a of state.answers) {
    if (state.found.has(a.id)) continue;
    if (a.keys.has(q)) return a;
  }
  for (const a of state.answers) {
    if (state.found.has(a.id)) continue;
    for (const key of a.keys) {
      if (key.length >= 4 && (key.includes(q) || q.includes(key)) && Math.abs(key.length - q.length) <= 3) {
        return a;
      }
    }
  }
  return null;
}

function renderAnswerLi(answer, opts = {}) {
  const li = document.createElement("li");
  const name = document.createElement("span");
  name.textContent = answer.name;
  li.appendChild(name);

  const obs = document.createElement("span");
  obs.className = "obscurity" + (answer.obscurity != null && answer.obscurity >= 0.75 ? " rare" : "");
  if (answer.obscurity != null) {
    obs.textContent = `obs ${answer.obscurity.toFixed(2)}`;
  } else {
    obs.textContent = "—";
  }
  li.appendChild(obs);
  if (opts.cls) li.classList.add(opts.cls);
  return li;
}

function handleSubmit(ev) {
  ev.preventDefault();
  const input = $("answer-input");
  const match = findMatch(input.value);
  if (!match) {
    setFeedback("No match.", "bad");
  } else if (state.found.has(match.id)) {
    setFeedback(`Already found: ${match.name}`, "bad");
  } else {
    state.found.add(match.id);
    $("found-list").prepend(renderAnswerLi(match));
    const flair = match.obscurity != null && match.obscurity >= 0.75 ? "  (obscure!)" : "";
    setFeedback(`✓ ${match.name}${flair}`, "good");
    updateProgress();
  }
  input.value = "";
  input.focus();
}

function giveUp() {
  const remaining = state.answers
    .filter((a) => !state.found.has(a.id))
    .sort((a, b) => (b.obscurity ?? 0) - (a.obscurity ?? 0));
  const list = $("missed-list");
  list.innerHTML = "";
  for (const a of remaining) list.appendChild(renderAnswerLi(a));
  $("missed-section").hidden = false;
  setFeedback(`Revealed ${remaining.length} missed answer(s).`, "");
  $("answer-input").disabled = true;
}

function wireUp() {
  $("start").addEventListener("click", () => startQuiz($("category").value));
  $("answer-form").addEventListener("submit", handleSubmit);
  $("give-up").addEventListener("click", giveUp);
}

(async function init() {
  wireUp();
  try {
    await loadCatalog();
  } catch (err) {
    $("picker-meta").textContent = `Failed to load data: ${err.message}`;
  }
})();
