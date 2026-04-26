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
    button.addEventListener("click", () => {
      state.mode = button.dataset.mode;
      renderAll();
      if (state.mode === "revise" && !state.revise.question) {
        startQuestion();
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
  return row;
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
