const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://backend-production-ffba0.up.railway.app/api";

function parseSSEBuffer(buffer, onEvent) {
  const events = buffer.split("\n\n");
  const remaining = events.pop() ?? "";

  for (const evt of events) {
    const lines = evt.split("\n");
    const dataLine = lines.find((line) => line.startsWith("data: "));
    if (!dataLine) continue;

    const payload = dataLine.slice(6);
    try {
      const parsed = JSON.parse(payload);
      onEvent(parsed);
    } catch {
      onEvent({ type: "text", data: payload });
    }
  }

  return remaining;
}

export async function streamFactCheck(query, mode, onData) {
  const res = await fetch(`${API_BASE}/fact-check-stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, mode }),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Fact check failed with status ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  let done = false;
  let buffer = "";

  while (!done) {
    const { value, done: doneReading } = await reader.read();
    done = doneReading;

    if (value) {
      buffer += decoder.decode(value, { stream: true });
      buffer = parseSSEBuffer(buffer, onData);
    }
  }

  if (buffer.trim()) {
    parseSSEBuffer(`${buffer}\n\n`, onData);
  }
}

export async function transcribeAudio(blob) {
  const formData = new FormData();
  formData.append("file", blob, "recording.webm");

  const res = await fetch(`${API_BASE}/voice-transcribe`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Voice transcription failed with status ${res.status}`);
  }

  return res.json();
}

export async function verifyImage(file, query) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("query", query || "");

  const res = await fetch(`${API_BASE}/image-verify`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Image verification failed with status ${res.status}`);
  }

  return res.json();
}
