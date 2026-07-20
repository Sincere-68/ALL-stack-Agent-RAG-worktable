const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

// ===== Chat =====
export async function sendMessage(prompt, conversationId = null, toolHint = null) {
  const body = { prompt };
  if (conversationId) body.conversation_id = conversationId;
  if (toolHint) body.tool_hint = toolHint;

  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ===== Conversations =====
export async function listConversations() {
  const res = await fetch(`${API_BASE_URL}/conversations`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function createConversation(title = "New Chat") {
  const res = await fetch(`${API_BASE_URL}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function deleteConversation(convId) {
  const res = await fetch(`${API_BASE_URL}/conversations/${convId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getConversationMessages(convId) {
  const res = await fetch(`${API_BASE_URL}/conversations/${convId}/messages`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ===== Knowledge =====
export async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE_URL}/knowledge/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getKnowledgeStats() {
  const res = await fetch(`${API_BASE_URL}/knowledge/stats`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function deleteKnowledge(filename) {
  const res = await fetch(`${API_BASE_URL}/knowledge/${filename}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function listDocuments() {
  const res = await fetch(`${API_BASE_URL}/knowledge/list`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export function getKnowledgeFileUrl(filename) {
  return `${API_BASE_URL}/knowledge/file/${encodeURIComponent(filename)}`;
}
