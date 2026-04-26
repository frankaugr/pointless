const STORAGE_KEY = "pointless-revision-v1";

export function loadProgress() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (_err) {
    return {};
  }
}

export function saveProgress(progress) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
}

export function answerKey(categorySlug, answerId) {
  return `${categorySlug}:${answerId}`;
}

export function getAnswerStatus(progress, categorySlug, answerId) {
  return progress[answerKey(categorySlug, answerId)] || "";
}

export function setAnswerStatus(progress, categorySlug, answerId, status) {
  const key = answerKey(categorySlug, answerId);
  if (!status) {
    delete progress[key];
  } else {
    progress[key] = status;
  }
  saveProgress(progress);
}

export function progressCounts(progress, categorySlug, answers) {
  const counts = { known: 0, needsWork: 0 };
  for (const answer of answers) {
    const status = getAnswerStatus(progress, categorySlug, answer.id);
    if (status === "known") counts.known += 1;
    if (status === "needs-work") counts.needsWork += 1;
  }
  return counts;
}
