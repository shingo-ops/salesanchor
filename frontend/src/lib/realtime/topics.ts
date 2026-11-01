// ADR-1016: 即時反映の topic 名。backend/app/realtime/topics.py と同じ集合に保つ（試験で照合）。
export const TOPICS = {
  tcgReview: "tcg.review",
  tcgInventory: "tcg.inventory",
  authLoginRequest: "auth.login_request",
} as const;
