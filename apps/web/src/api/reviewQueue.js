import { apiFetch } from "./client.js";

export async function fetchReviewQueue(statusFilter = "all") {
  return apiFetch(`/review-queue?status_filter=${encodeURIComponent(statusFilter)}`);
}

export async function fetchReviewQueueItem(id) {
  return apiFetch(`/review-queue/${encodeURIComponent(id)}`);
}

export async function submitReviewAction(id, action, editedAnswer = null, notes = null) {
  return apiFetch(`/review-queue/${encodeURIComponent(id)}/action`, {
    method: "POST",
    body: JSON.stringify({
      action,
      edited_answer: editedAnswer,
      notes,
    }),
  });
}

