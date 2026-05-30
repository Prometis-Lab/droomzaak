import type { AgentResponse, ChapterState } from "./types";

const SESSION_KEY = "droomzaak.session-id";

export function getSessionId(): string {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID().replace(/-/g, "");
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export function newSession(): string {
  const id = crypto.randomUUID().replace(/-/g, "");
  localStorage.setItem(SESSION_KEY, id);
  return id;
}

export async function sendChat(
  message: string,
  sessionId: string,
  context: Record<string, unknown> = {},
): Promise<AgentResponse> {
  const res = await fetch("/api/agent/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, context }),
  });
  if (!res.ok) throw new Error(`chat failed: ${res.status}`);
  return res.json();
}

export async function getChapter(sessionId: string): Promise<{ chapter_state: ChapterState }> {
  const res = await fetch(`/api/droomzaak/chapter/${sessionId}`);
  if (!res.ok) throw new Error(`getChapter failed: ${res.status}`);
  return res.json();
}

export async function putChapter(
  sessionId: string,
  patch: Record<string, unknown>,
): Promise<{ chapter_state: ChapterState }> {
  const res = await fetch(`/api/droomzaak/chapter/${sessionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patch }),
  });
  if (!res.ok) throw new Error(`putChapter failed: ${res.status}`);
  return res.json();
}
