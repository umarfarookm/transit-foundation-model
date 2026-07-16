import type { FeedUploadResponse, ChatResponse } from "./types";

const API_BASE = "http://localhost:8000";

export async function uploadFeed(file: File): Promise<FeedUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/feed/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Upload failed: ${res.status}`);
  }

  return res.json();
}

export async function askFeedQuestion(
  uploadId: string,
  question: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/feed/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ upload_id: uploadId, question }),
  });

  if (!res.ok) {
    throw new Error(`Ask failed: ${res.status}`);
  }

  return res.json();
}

export async function chatQuestion(question: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    throw new Error(`Chat failed: ${res.status}`);
  }

  return res.json();
}
