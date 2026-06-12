import {
  displayFields,
  loadCatalog,
  loadCategory,
  lowScoreCount,
  pointlessScore,
  rareCount,
  scoreBand,
  sortAnswers,
} from "./js/data.js";
import { buildAnswerIndex, findMatches } from "./js/match.js";
import { bestFound, flattenRounds, pickRound, roundKey } from "./js/play.js";
import { buildQuestionCandidates, pickQuestion } from "./js/questions.js";
import {
  getAnswerStatus,
  loadProgress,
  progressCounts,
  setAnswerStatus,
} from "./js/storage.js";

const state = {
  catalog: [],
  categories: new Map(),
  activeSlug: "",
  mode: "learn",
  progress: loadProgress(),
  learn: {
    sort: "obscurity",
    filter: "all",
    hideNames: false,
    showHighScores: false,
    revealed: new Set(),
  },
  revise: {
    question: null,
    found: new Set(),
    answerIndex: null,
    revealed: false,
  },
  play: {
    rounds: null,
    round: null,
    found: new Set(),
    answerIndex: null,
    revealed: false,
  },
};

const $ = (id) => document.getElementById(id);

async function init() {
  bindChrome();
  try {
    state.catalog = await loadCatalog();
    state.activeSlug = state.catalog[0]?.slug || "";
    renderCategoryNav();
    await ensureCategory(state.activeSlug);
    renderAll();
  } catch (err) {
    $("app-error").textContent = err.message;
    $("app-error").hidden = false;
  }
}

function bindChrome() {
  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.mode = button.dataset.mode;
      if (state.mode === "play") {
        await ensurePlayData();
      }
      renderAll();
      if (state.mode === "revise" && !state.revise.question) {
        startQuestion();
      }
      if (state.mode === "play" && !state.play.round) {
        startRound();
      }
    });
  });

  $("learn-sort").addEventListener("change", (event) => {
    state.learn.sort = event.target.value;
    renderLearn();
  });
  $("learn-filter").addEventListener("change", (event) => {
    state.learn.filter = event.target.value;
    renderLearn();
  });
  $("hide-names").addEventListener("change", (event) => {
    state.learn.hideNames = event.target.checked;
    state.learn.revealed = new Set();
    renderLearn();
  });
  $("show-high-scores").addEventListener("change", (event) => {
    state.learn.showHighScores = event.target.checked;
    renderAll();
  });
  $("reveal-all").addEventListener("click", () => {
    const category = activeCategory();
    state.learn.revealed = new Set(category.answers.map((answer) => answer.id));
    renderLearn();
  });

  $("new-question").addEventListener("click", startQuestion);
  $("answer-form").addEventListener("submit", handleAnswerSubmit);
  $("give-up").addEventListener("click", revealMissed);

  $("new-round").addEventListener("click", startRound);
  $("play-form").addEventListener("submit", handlePlaySubmit);
  $("play-reveal").addEventListener("click", revealBoard);
}

async function ensureCategory(slug) {
  if (!slug || state.categories.has(slug)) return;
  const category = await loadCategory(slug);
  state.categories.set(slug, category);
}

function activeCategory() {
  return state.categories.get(state.activeSlug);
}

function renderCategoryNav() {
  const list = $("category-list");
  list.innerHTML = "";
  for (const category of state.catalog) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "category-button";
    button.dataset.slug = category.slug;
    button.innerHTML = `
      <span>${escapeHtml(category.name)}</span>
      <strong>${category.n_answers}</strong>
    `;
    button.addEventListener("click", async () => {
      state.activeSlug = category.slug;
      state.learn.revealed = new Set();
      state.revise.question = null;
      state.revise.found = new Set();
      state.revise.revealed = false;
      await ensureCategory(category.slug);
      renderAll();
      if (state.mode === "revise") startQuestion();
    });
    list.appendChild(button);
  }
}

function renderAll() {
  const category = activeCategory();
  if (!category) return;

  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === state.mode);
    button.setAttribute("aria-pressed", button.dataset.mode === state.mode ? "true" : "false");
  });
  document.querySelectorAll(".category-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.slug === state.activeSlug);
  });

  $("learn-view").hidden = state.mode !== "learn";
  $("revise-view").hidden = state.mode !== "revise";
  $("play-view").hidden = state.mode !== "play";

  if (state.mode === "play") {
    $("active-category-name").textContent = "Play along";
    $("active-category-description").textContent =
      "Real rounds from series 34-35. Give answers, then compare against what the 100 people actually said.";
    $("category-stats").textContent = state.play.rounds
      ? `${state.play.rounds.length} rounds extracted from broadcast episodes`
      : "";
    renderRound();
    return;
  }

  $("active-category-name").textContent = category.name;
  $("active-category-description").textContent = category.description;

  const counts = progressCounts(state.progress, category.slug, category.answers);
  const lowScores = lowScoreCount(category.answers);
  const hiddenHigh = category.n_answers - lowScores;
  $("category-stats").textContent = `${category.n_answers} answers - ${lowScores} score 0-50 - ${hiddenHigh} above 50 - ${counts.known} known - ${counts.needsWork} needs work`;

  renderLearn();
  renderReviseShell();
}

function renderLearn() {
  const category = activeCategory();
  if (!category || state.mode !== "learn") return;

  const answers = sortAnswers(filterLearnAnswers(category), state.learn.sort);
  const list = $("learn-list");
  list.innerHTML = "";
  const hiddenHigh = state.learn.showHighScores
    ? 0
    : category.answers.filter((answer) => pointlessScore(answer) > 50).length;
  $("learn-count").textContent = hiddenHigh > 0
    ? `${answers.length} shown - ${hiddenHigh} hidden above 50`
    : `${answers.length} shown`;

  for (const answer of answers) {
    list.appendChild(renderLearnRow(category, answer));
  }
}

function filterLearnAnswers(category) {
  return category.answers.filter((answer) => {
    const status = getAnswerStatus(state.progress, category.slug, answer.id);
    const score = pointlessScore(answer);
    if (!state.learn.showHighScores && score > 50) return false;
    if (state.learn.filter === "rare") return score <= 30;
    if (state.learn.filter === "known") return status === "known";
    if (state.learn.filter === "needs-work") return status === "needs-work";
    if (state.learn.filter === "unmarked") return !status;
    return true;
  });
}

function renderLearnRow(category, answer) {
  const row = document.createElement("article");
  const status = getAnswerStatus(state.progress, category.slug, answer.id);
  const isHidden = state.learn.hideNames && !state.learn.revealed.has(answer.id);
  row.className = `answer-row ${status}`;

  const name = document.createElement("div");
  name.className = "answer-name";
  name.textContent = isHidden ? "Hidden answer" : answer.name;

  const meta = document.createElement("div");
  meta.className = "answer-meta";
  meta.append(...displayFields(category, answer).map(renderFieldPill));
  meta.append(renderObscurity(answer));

  const actions = document.createElement("div");
  actions.className = "row-actions";
  if (isHidden) {
    actions.append(actionButton("Reveal", () => {
      state.learn.revealed.add(answer.id);
      renderLearn();
    }));
  }
  actions.append(statusButton("Known", status === "known", () => {
    setAnswerStatus(state.progress, category.slug, answer.id, status === "known" ? "" : "known");
    renderAll();
  }));
  actions.append(statusButton("Needs work", status === "needs-work", () => {
    setAnswerStatus(state.progress, category.slug, answer.id, status === "needs-work" ? "" : "needs-work");
    renderAll();
  }));

  row.append(name, meta, actions);
  const evidence = answer.obscurity?.evidence || [];
  if (!isHidden && evidence.length > 0) {
    row.append(renderEvidence(evidence));
  }
  return row;
}

function renderEvidence(evidence) {
  const details = document.createElement("details");
  details.className = "answer-evidence";
  const summary = document.createElement("summary");
  summary.textContent = `Seen on the show (${evidence.length})`;
  details.append(summary);

  const list = document.createElement("ul");
  for (const item of evidence) {
    const li = document.createElement("li");
    const line = `Scored ${item.score_0_to_100} - ${item.episode}` +
      (item.question_text ? ` - ${item.question_text}` : "");
    li.append(document.createTextNode(line));
    if (item.quote) {
      const quote = document.createElement("q");
      quote.textContent = item.quote;
      li.append(document.createElement("br"), quote);
    }
    list.append(li);
  }
  details.append(list);
  return details;
}

function renderReviseShell() {
  const category = activeCategory();
  if (!category || state.mode !== "revise") return;
  const candidates = buildQuestionCandidates(category).filter((candidate) => candidate.eligible);
  $("question-pool").textContent = `${candidates.length} usable question patterns for ${category.name}`;
  renderQuestion();
}

function startQuestion() {
  const category = activeCategory();
  if (!category) return;
  const question = pickQuestion(category);
  state.revise.question = question || {
    id: "fallback",
    prompt: `Name any ${category.name}`,
    answers: category.answers,
    answerCount: category.answers.length,
    rareCount: rareCount(category.answers),
  };
  state.revise.found = new Set();
  state.revise.revealed = false;
  state.revise.answerIndex = buildAnswerIndex(state.revise.question.answers);
  $("answer-input").disabled = false;
  $("answer-input").value = "";
  $("answer-input").focus();
  renderQuestion();
}

function renderQuestion() {
  const category = activeCategory();
  const question = state.revise.question;
  if (!category || !question) {
    $("question-card").hidden = true;
    return;
  }

  $("question-card").hidden = false;
  $("question-title").textContent = question.prompt;
  $("question-meta").textContent = `${question.answerCount} valid answers - ${question.rareCount} strong low-score targets`;
  $("revise-progress").textContent = `${state.revise.found.size} / ${question.answerCount} found`;
  $("feedback").textContent = "";
  $("ambiguity").innerHTML = "";

  renderFoundList();
  renderMissedList();
}

function handleAnswerSubmit(event) {
  event.preventDefault();
  const input = $("answer-input");
  const value = input.value;
  const result = findMatches(value, state.revise.answerIndex, state.revise.found);
  input.value = "";

  if (result.status === "match") {
    acceptAnswer(result.matches[0]);
  } else if (result.status === "ambiguous") {
    showAmbiguity(result.matches);
  } else if (result.status === "duplicate") {
    setFeedback("Already found.", "bad");
  } else {
    setFeedback("No match for this question.", "bad");
  }
}

function acceptAnswer(answer) {
  state.revise.found.add(answer.id);
  const suffix = pointlessScore(answer) <= 30 ? " - strong low scorer" : "";
  setFeedback(`${answer.name}${suffix}`, "good");
  $("ambiguity").innerHTML = "";
  if (state.revise.found.size === state.revise.question.answerCount) {
    setFeedback("Complete set found.", "good");
  }
  renderFoundList();
  renderMissedList();
  $("revise-progress").textContent = `${state.revise.found.size} / ${state.revise.question.answerCount} found`;
}

function showAmbiguity(matches) {
  const wrap = $("ambiguity");
  wrap.innerHTML = "";
  const label = document.createElement("span");
  label.textContent = "Did you mean";
  wrap.appendChild(label);
  for (const answer of matches) {
    wrap.append(actionButton(answer.name, () => acceptAnswer(answer)));
  }
  setFeedback("More than one valid answer matches that text.", "bad");
}

function renderFoundList() {
  const list = $("found-list");
  list.innerHTML = "";
  const found = state.revise.question.answers
    .filter((answer) => state.revise.found.has(answer.id))
    .sort((a, b) => (b.obscurity.score ?? 0) - (a.obscurity.score ?? 0));
  for (const answer of found) {
    list.append(renderCompactAnswer(answer));
  }
}

function renderMissedList() {
  const section = $("missed-section");
  const list = $("missed-list");
  list.innerHTML = "";
  section.hidden = !state.revise.revealed;
  if (!state.revise.revealed) return;

  const missed = state.revise.question.answers
    .filter((answer) => !state.revise.found.has(answer.id))
    .sort((a, b) => (b.obscurity.score ?? 0) - (a.obscurity.score ?? 0));
  for (const answer of missed) {
    list.append(renderCompactAnswer(answer));
  }
}

function revealMissed() {
  if (!state.revise.question) return;
  state.revise.revealed = true;
  $("answer-input").disabled = true;
  setFeedback("Remaining answers revealed, most obscure first.", "");
  renderMissedList();
}

async function ensurePlayData() {
  if (state.play.rounds) return;
  try {
    const response = await fetch("data/episodes.json", { cache: "no-cache" });
    if (!response.ok) throw new Error(`Failed to load data/episodes.json: ${response.status}`);
    state.play.rounds = flattenRounds(await response.json());
  } catch (err) {
    state.play.rounds = [];
    $("round-pool").textContent = err.message;
  }
}

function startRound() {
  const previous = state.play.round ? roundKey(state.play.round) : "";
  const round = pickRound(state.play.rounds || [], previous);
  state.play.round = round;
  state.play.found = new Set();
  state.play.revealed = false;
  state.play.answerIndex = round ? buildAnswerIndex(round.answers) : null;
  $("play-input").disabled = false;
  $("play-input").value = "";
  if (round) $("play-input").focus();
  renderRound();
}

function renderRound() {
  const round = state.play.round;
  $("round-pool").textContent = state.play.rounds
    ? `${state.play.rounds.length} rounds available`
    : "";
  if (!round) {
    $("round-card").hidden = true;
    return;
  }

  $("round-card").hidden = false;
  $("round-episode").textContent = round.episodeLabel;
  $("round-title").textContent = round.category;
  $("round-meta").textContent =
    `${round.answers.length} answers heard in the episode` +
    (round.confidence !== "high" ? " - category wording reconstructed from dialogue" : "");
  $("play-progress").textContent = playProgressText();
  setPlayFeedback("");
  renderPlayLists();
}

function playProgressText() {
  const best = bestFound(state.play.round, state.play.found);
  if (!best) return `${state.play.found.size} found`;
  return `${state.play.found.size} found - best ${best.obscurity.pointless_score}`;
}

function handlePlaySubmit(event) {
  event.preventDefault();
  const input = $("play-input");
  const result = findMatches(input.value, state.play.answerIndex, state.play.found);
  input.value = "";

  if (result.status === "match") {
    const answer = result.matches[0];
    state.play.found.add(answer.id);
    const score = answer.obscurity.pointless_score;
    setPlayFeedback(
      answer.isPointless || score === 0
        ? `${answer.name} - POINTLESS!`
        : `${answer.name} - ${score} of the 100 said it`,
      "good",
    );
  } else if (result.status === "ambiguous") {
    setPlayFeedback("More than one board answer matches - be more specific.", "bad");
  } else if (result.status === "duplicate") {
    setPlayFeedback("Already found.", "bad");
  } else {
    setPlayFeedback("Not on the board - the subtitles only carry part of it, so a good answer can still miss.", "bad");
  }
  $("play-progress").textContent = playProgressText();
  renderPlayLists();
}

function revealBoard() {
  if (!state.play.round) return;
  state.play.revealed = true;
  $("play-input").disabled = true;
  setPlayFeedback("Board revealed, lowest scores first.", "");
  renderPlayLists();
}

function renderPlayLists() {
  const round = state.play.round;
  if (!round) return;

  const foundList = $("play-found");
  foundList.innerHTML = "";
  const found = round.answers
    .filter((answer) => state.play.found.has(answer.id))
    .sort((a, b) => a.obscurity.pointless_score - b.obscurity.pointless_score);
  for (const answer of found) {
    foundList.append(renderCompactAnswer(answer));
  }

  const section = $("play-board-section");
  section.hidden = !state.play.revealed;
  if (!state.play.revealed) return;
  const board = $("play-board");
  board.innerHTML = "";
  const sorted = [...round.answers].sort(
    (a, b) => a.obscurity.pointless_score - b.obscurity.pointless_score,
  );
  for (const answer of sorted) {
    const li = renderCompactAnswer(answer);
    if (state.play.found.has(answer.id)) li.className = "board-found";
    board.append(li);
  }
}

function setPlayFeedback(message, kind = "") {
  const el = $("play-feedback");
  el.textContent = message;
  el.className = `feedback ${kind}`;
}

function renderCompactAnswer(answer) {
  const li = document.createElement("li");
  li.append(document.createTextNode(answer.name));
  li.append(renderObscurity(answer));
  return li;
}

function renderFieldPill(item) {
  const span = document.createElement("span");
  span.className = "field-pill";
  span.textContent = `${item.label}: ${item.value}`;
  return span;
}

function renderObscurity(answer) {
  const span = document.createElement("span");
  const score = pointlessScore(answer);
  const band = scoreBand(score);
  span.className = `score-pill ${answer.obscurity.confidence} ${score > 50 ? "high-score" : ""}`;
  span.title = `Estimated Pointless score ${score}/100; lower is better; confidence ${answer.obscurity.confidence}`;
  span.textContent = `${score} pts ${band}`;
  return span;
}

function actionButton(label, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "subtle-button";
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function statusButton(label, active, onClick) {
  const button = actionButton(label, onClick);
  button.classList.toggle("active", active);
  return button;
}

function setFeedback(message, kind = "") {
  const el = $("feedback");
  el.textContent = message;
  el.className = `feedback ${kind}`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[ch]);
}

init();
