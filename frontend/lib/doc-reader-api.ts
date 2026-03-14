/**
 * API client for the Document Reader feature.
 * Communicates with the /api/docreader/* backend endpoints.
 */

const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "") +
  "/api/docreader";

// ── Types ────────────────────────────────────────────────────────────────

export interface DocumentMeta {
  id: string;
  title: string;
  file_path: string;
  uploaded_at: string;
}

export interface UploadResult {
  document_id: string;
  title: string;
  chunks: number;
}

// ── Helpers ──────────────────────────────────────────────────────────────

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.ok) return res.json() as Promise<T>;

  let message = `Request failed (${res.status})`;
  try {
    const data = await res.json();
    message =
      (data.detail as string) ||
      (data.error as string) ||
      (data.message as string) ||
      message;
  } catch {
    // ignore JSON parse errors
  }
  throw new Error(message);
}

// ── API functions ────────────────────────────────────────────────────────

export async function getDocuments(): Promise<DocumentMeta[]> {
  const res = await fetch(`${API_BASE}/documents`);
  return handleResponse<DocumentMeta[]>(res);
}

export function getPdfUrl(documentId: string): string {
  return `${API_BASE}/pdf/${documentId}`;
}

export async function uploadDocument(file: File): Promise<UploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<UploadResult>(res);
}

/**
 * Stream a response from an SSE endpoint.
 * Calls `onChunk` with each token as it arrives.
 * Returns the full concatenated string when done.
 */
export async function streamPost(
  endpoint: "/explain/stream" | "/ask/stream",
  body: Record<string, string>,
  onChunk: (token: string) => void,
): Promise<string> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      message = (data.detail as string) || message;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let full = "";
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by double newline
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6);
      if (data === "[DONE]") return full;
      if (data.startsWith("[ERROR]")) throw new Error(data.slice(7).trim());
      // Unescape newlines encoded by the backend
      const token = data.replace(/\\n/g, "\n");
      full += token;
      onChunk(token);
    }
  }

  return full;
}
