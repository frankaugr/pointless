import {loadCategory} from "./data.js";
import {normalise} from "./match.js";
import {MEMORY_KEY, categoryCards, schedule, makeQueue, counts, accepts, validateProgress} from "./memory.js";

const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
let mounted = false;

export async function mountMemory(catalog) {
  if (mounted) return;
  mounted = true;
  const root = document.getElementById("memory-view");
  let progress = {}, warning = "";
  try { progress = validateProgress(JSON.parse(localStorage.getItem(MEMORY_KEY) || "{}")); }
  catch { warning = "Saved memory progress could not be read. This session still works; export it to keep a copy."; }
  const sports = [...document.querySelectorAll(".cheat-card")].flatMap((section, index) => {
    const group = section.querySelector("h3").textContent.trim();
    return [...section.querySelectorAll("li")].map(li => {
      const name = li.querySelector("strong")?.textContent.trim();
      if (!name) return null;
      return {id: `sports-${index}:${normalise(name).replaceAll(" ", "-")}`, deck: `sports-${index}`,
        group, name, aliases: [], clue: (index === 4 ? "Grand Prix wins listed: " : "") + li.textContent.slice(li.textContent.indexOf(name) + name.length).replace(/^\s*[-–—]\s*/, "").trim(),
        scope: "Selected answers from the existing sports cheat sheet, not a complete answer set. Figures and scope are inherited from that sheet.",
        sourceLabel: "Original sports cheat sheet", source: "#cheatsheet"};
    }).filter(Boolean);
  });
  let cards = sports;
  let filter = "sports", view = "study", queue = [], position = 0, revealed = false, hinted = false;
  let sessionCards = [], grades = [], retryIds = new Set(), search = "", reverse = false, inSession = false;
  let mode = "due", size = 10;
  const decks = [{slug:"sports", name:"Sportspeople · all sports"},
    {slug:"politics", name:"Politicians · UK & US"},
    ...[...new Map(sports.map(c => [c.deck, {slug:c.deck, name:c.group}])).values()],
    ...catalog.map(c => ({slug:c.slug, name:c.name}))];
  root.innerHTML = `<div class="memory-controls"><label>Choose your deck<select id="memory-deck">${decks.map(d => `<option value="${esc(d.slug)}"${d.slug === "sports" || d.slug.startsWith("sports-") ? "" : " disabled"}>${esc(d.name)}</option>`).join("")}</select></label>
    <div class="memory-tabs" aria-label="Memory activity"><button id="memory-study" type="button" aria-pressed="true">Recall practice</button><button id="memory-browse" type="button" class="subtle-button" aria-pressed="false">Study the deck</button></div></div>
    <p id="memory-warning" class="memory-warning" role="status"></p><div id="memory-stats" class="memory-stats"></div>
    <div id="memory-content"></div><details class="memory-help"><summary>How to use this · progress & backups</summary>
    <p>Study five or ten names, then recall them without looking. Say the answer or type it. Use a hint if needed, reveal the card, then rate your recall honestly. “Again” adds a retry at the end of this session and schedules a review in 10 minutes; “With effort” schedules tomorrow; “Remembered” starts at 3 days and doubles on later successes, up to 180 days.</p>
    <p>Clues can fit more than one person. The name hint helps distinguish them. “Name → facts” lets you practise the connection in reverse; both directions share a review schedule. Memory practice includes all scores. Sports selections and political facts come from the existing site; no survey score is predicted here.</p>
    <p>Progress and personal cues are saved only in this browser. Export a backup before changing devices or clearing browser data. Import merges cards from your backup, keeping the more recently reviewed record when both exist.</p>
    <div class="memory-actions"><button type="button" id="memory-export" class="subtle-button">Export progress</button><label class="import-label">Import progress<input id="memory-import" type="file" accept="application/json,.json"></label></div></details>`;
  const $ = id => document.getElementById(id);
  function save() {
    try {localStorage.setItem(MEMORY_KEY, JSON.stringify(progress));}
    catch {warning = "Browser storage is unavailable or full. Export your progress before closing this page.";}
    $("memory-warning").textContent = warning;
  }
  function selected() {
    return cards.filter(c => filter === "sports" ? c.deck.startsWith("sports-")
      : filter === "politics" ? ["uk-prime-ministers", "us-presidents"].includes(c.deck) : c.deck === filter);
  }
  function renderStats() {
    const pool = selected(), totals = counts(pool, progress);
    $("memory-stats").innerHTML = [[pool.length,"cards in deck"],[totals.due,"due for review"],[totals.new,"not studied yet"],[totals.established,"spaced ≥ 6 days"]]
      .map(([n,label]) => `<div><strong>${n}</strong><span>${label}</span></div>`).join("");
    $("memory-warning").textContent = warning;
  }
  function start(nextMode = mode, explicitCards = null) {
    mode = nextMode;
    sessionCards = selected();
    queue = explicitCards || makeQueue(sessionCards, progress, mode, size);
    position = 0; grades = []; retryIds = new Set(); revealed = false; hinted = false; inSession = true;
    render();
  }
  function safeLink(card) {
    if (card.source === "#cheatsheet") return '<button type="button" id="memory-source" class="subtle-button">Original sports cheat sheet</button>';
    return /^https?:\/\//.test(card.source) ? `<a href="${esc(card.source)}" target="_blank" rel="noopener noreferrer">${esc(card.sourceLabel)}</a>` : "";
  }
  function render() {
    renderStats();
    $("memory-deck").disabled = inSession && position < queue.length;
    $("memory-study").setAttribute("aria-pressed", view === "study");
    $("memory-browse").setAttribute("aria-pressed", view === "browse");
    const content = $("memory-content");
    if (view === "browse") {renderBrowse(); return;}
    if (!inSession) {
      content.innerHTML = `<div class="memory-start"><p class="eyebrow">A little, often</p><h3>Make the names stick.</h3><p>Connect a name to a few facts. Recall it, check it, then revisit it when it’s due.</p>
        <div class="memory-session-options"><label>Session length<select id="memory-size"><option value="5">5 cards</option><option value="10">10 cards</option><option value="20">20 cards</option></select></label>
        <label>Practice<select id="memory-direction"><option value="forward">Facts → name</option><option value="reverse">Name → facts</option></select></label></div>
        <div class="memory-actions"><button id="memory-start" type="button">Start due + new cards</button><button id="memory-weak" type="button" class="subtle-button">Practise difficult cards</button><button id="memory-all" type="button" class="subtle-button">Practise any cards</button></div>
        <p class="tool-meta">Overdue cards come first. New cards fill the remaining places. A session takes a few minutes.</p></div>`;
      $("memory-size").value = size;
      $("memory-direction").value = reverse ? "reverse" : "forward";
      $("memory-size").onchange = e => size = Number(e.target.value);
      $("memory-direction").onchange = e => reverse = e.target.value === "reverse";
      $("memory-start").onclick = () => start("due");
      $("memory-weak").onclick = () => start("weak");
      $("memory-all").onclick = () => start("all");
      return;
    }
    if (position >= queue.length) {
      const missed = sessionCards.filter(c => retryIds.has(c.id));
      const totals = counts(selected(), progress);
      content.innerHTML = `<div class="memory-start"><p class="eyebrow">${queue.length ? "Session complete" : "Nothing in this queue"}</p><h3>${queue.length ? "A few names closer." : "You’re ready for a different deck."}</h3>
        <p>${queue.length ? `${grades.filter(g => g === "good").length} remembered · ${grades.filter(g => g === "hard").length} with effort · ${grades.filter(g => g === "again").length} missed, across ${grades.length} reviews (including retries).` : mode === "weak" ? "No cards are currently marked difficult. Start a recall session first." : "No due or unseen cards remain. You can still practise any cards."}</p>
        <p>${totals.due} due now · ${totals.new} unseen in this deck. Your review dates are saved as you go.</p><div class="memory-actions"><button id="memory-next-session" type="button">Choose next session</button>${missed.length ? '<button id="memory-retry" type="button" class="subtle-button">Practise missed names again</button>' : ""}</div></div>`;
      $("memory-next-session").onclick = () => {inSession = false; render();};
      if (missed.length) $("memory-retry").onclick = () => start("all", missed);
      return;
    }
    const card = queue[position];
    const sameClue = sessionCards.filter(c => c.group === card.group && c.clue === card.clue).length > 1;
    content.innerHTML = `<div class="memory-session-head"><span>Review ${position + 1} of ${queue.length}${retryIds.has(card.id) ? " · retry" : ""}</span><button id="memory-end" type="button" class="subtle-button">End session</button></div>
      <progress class="memory-meter" max="${queue.length}" value="${position}" aria-label="Session progress"></progress>
      <article class="memory-card"><p class="eyebrow">${esc(card.group)}</p><p class="memory-prompt">${reverse ? "Recall the facts behind this name" : "Who fits these facts?"}</p><h3 tabindex="-1" id="memory-question">${esc(reverse ? card.name : card.clue)}</h3>
      ${!reverse && sameClue ? `<p class="tool-meta">Several cards share these facts. This name starts with ${esc(card.name.split(/\s+/).map(w => w[0]).join(" "))}.</p>` : ""}
      ${!revealed ? `<form id="memory-answer-form" autocomplete="off">${!reverse ? '<label class="sr-only" for="memory-answer">Your answer</label><input id="memory-answer" type="text" placeholder="Say the name, or type it here…" spellcheck="false" autocapitalize="off"><button type="submit">Check answer</button>' : '<p>Say the achievement, dates or party aloud before revealing.</p><button type="submit">Reveal facts</button>'}</form>
      <p id="memory-feedback" role="status"></p><p id="memory-hint-text" class="memory-hint" role="status"></p><div class="memory-actions"><button id="memory-hint" type="button" class="subtle-button">${reverse ? "Fact hint" : "Name hint"}</button>${!reverse ? '<button id="memory-reveal" type="button" class="subtle-button">Reveal answer</button>' : ""}</div>` : `<div class="memory-answer-panel"><p class="eyebrow">${reverse ? "The connection" : "The answer"}</p><h4>${esc(reverse ? card.clue : card.name)}</h4><p>${esc(card.scope)}</p>${safeLink(card)}
      <label for="memory-note">Your memory cue <span class="tool-meta">· private to this browser</span></label><textarea id="memory-note" maxlength="1000" rows="2" placeholder="Link the name to a vivid image, sound or person you know…">${esc(progress[card.id]?.note || "")}</textarea><button id="memory-save-note" type="button" class="subtle-button">Save cue</button><span id="memory-note-status" role="status"></span></div>
      <p>${hinted ? "You used a hint. Choose Again or With effort if the clue did the work." : "How well did you recall it before revealing?"}</p><div class="memory-ratings"><button data-grade="again" type="button">Again <small>Retry + 10 min</small></button><button data-grade="hard" type="button">With effort <small>1 day</small></button><button data-grade="good" type="button">Remembered <small>${schedule(progress[card.id], "good").interval} days</small></button></div>`}</article>`;
    $("memory-end").onclick = () => {inSession = false; render();};
    if (!revealed) {
      $("memory-answer-form").onsubmit = e => {
        e.preventDefault();
        if (reverse || accepts($("memory-answer").value, card, sessionCards)) {revealed = true; render(); $("memory-question").focus();}
        else $("memory-feedback").textContent = "Not a match for this card. Try the full name, use a hint, or reveal and check it yourself.";
      };
      if (!reverse) $("memory-reveal").onclick = () => {revealed = true; render(); $("memory-question").focus();};
      $("memory-hint").onclick = () => {
        hinted = true;
        $("memory-hint-text").textContent = (reverse ? card.clue.split(" · ")[0] : card.name.split(/\s+/).map(word => word[0] + "·".repeat(Math.max(0, word.length - 1))).join(" "))
          + (progress[card.id]?.note ? ` — Your cue: ${progress[card.id].note}` : "");
      };
    } else {
      const saveNote = () => {progress[card.id] = {...progress[card.id], note: $("memory-note").value}; save();};
      $("memory-save-note").onclick = () => {saveNote(); $("memory-note-status").textContent = warning ? "Kept for this session; export a backup." : " Cue saved.";};
      if ($("memory-source")) $("memory-source").onclick = () => document.querySelector('[data-mode="cheatsheet"]').click();
      root.querySelectorAll("[data-grade]").forEach(button => button.onclick = () => {
        saveNote();
        const grade = button.dataset.grade;
        progress[card.id] = schedule(progress[card.id], grade); save(); grades.push(grade);
        if (grade === "again" && !retryIds.has(card.id)) {retryIds.add(card.id); queue.push(card);}
        position++; revealed = false; hinted = false; render();
        ($(reverse ? "memory-question" : "memory-answer") || $("memory-next-session"))?.focus();
      });
    }
  }
  function renderBrowse() {
    $("memory-content").innerHTML = `<div class="memory-browse-heading"><label for="memory-search">Find a name or fact</label><input id="memory-search" type="text" placeholder="Try a surname, party, year or sport…" value="${esc(search)}"></div><p class="tool-meta">Build a small set of connections first. Open a card to add your own memory cue.</p><div id="memory-library" class="memory-library"></div>`;
    $("memory-search").oninput = e => {search = e.target.value; renderLibrary();};
    renderLibrary();
  }
  function renderLibrary() {
    const rows = selected().filter(c => normalise(`${c.name} ${c.clue} ${c.group}`).includes(normalise(search)))
      .sort((a,b) => a.group.localeCompare(b.group) || a.clue.localeCompare(b.clue, undefined, {numeric:true}) || a.name.localeCompare(b.name));
    $("memory-library").innerHTML = rows.length ? rows.map(c => `<details class="memory-library-card"><summary><span>${esc(c.name)}</span><small>${esc(c.group)}</small></summary><p>${esc(c.clue)}</p><p class="tool-meta">${esc(c.scope)}</p><label>Your memory cue<textarea data-note="${esc(c.id)}" maxlength="1000" rows="2" placeholder="What will make this name stick?">${esc(progress[c.id]?.note || "")}</textarea></label><button type="button" data-save="${esc(c.id)}" class="subtle-button">Save cue</button><span class="cue-status" role="status"></span></details>`).join("") : '<p>No matching cards. Try another name or fact.</p>';
    $("memory-library").querySelectorAll("[data-save]").forEach(button => button.onclick = () => {
      const id = button.dataset.save;
      progress[id] = {...progress[id], note: button.parentElement.querySelector("textarea").value}; save();
      button.nextElementSibling.textContent = warning ? " Kept in session; export a backup." : " Cue saved.";
    });
  }
  $("memory-deck").onchange = e => {filter = e.target.value; inSession = false; search = ""; render();};
  $("memory-study").onclick = () => {view = "study"; render();};
  $("memory-browse").onclick = () => {view = "browse"; render();};
  $("memory-export").onclick = () => {
    const blob = new Blob([JSON.stringify({version:1, progress}, null, 2)], {type:"application/json"});
    const url = URL.createObjectURL(blob), link = document.createElement("a");
    link.href = url; link.download = "pointless-memory-progress.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  $("memory-import").onchange = async e => {
    const file = e.target.files[0]; if (!file) return;
    try {
      if (file.size > 5000000) throw new Error("File is too large");
      const backup = JSON.parse(await file.text());
      if (backup.version !== 1) throw new Error("Unsupported backup version");
      const incoming = validateProgress(backup.progress);
      for (const [id, row] of Object.entries(incoming)) {
        if (!progress[id] || (row.lastReviewed || 0) >= (progress[id].lastReviewed || 0)) progress[id] = row;
      }
      warning = "Backup imported. Your existing Learn-mode marks are unchanged."; save(); render();
    } catch {warning = "That file is not a valid memory backup. Your progress has not been changed."; $("memory-warning").textContent = warning;}
    e.target.value = "";
  };
  render();
  // Keep the sports deck immediately usable while other decks load.
  const results = await Promise.allSettled(catalog.map(c => loadCategory(c.slug)));
  cards = [...sports, ...results.flatMap(r => r.status === "fulfilled" ? categoryCards(r.value) : [])];
  for (const option of $("memory-deck").options) {
    option.disabled = option.value === "politics"
      ? !cards.some(c => ["uk-prime-ministers", "us-presidents"].includes(c.deck))
      : option.value !== "sports" && !cards.some(c => c.deck === option.value);
  }
  if (results.some(r => r.status === "rejected")) warning = "Some decks could not load. Check your connection and reload to try again.";
  if (!inSession) render(); else renderStats();
}
