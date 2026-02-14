export async function streamFactCheck(query, mode, onData) {
  const res = await fetch("http://localhost:8000/fact-check-stream", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ query, mode })
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  let done = false;

  while (!done) {
    const { value, done: doneReading } = await reader.read();
    done = doneReading;

    const chunk = decoder.decode(value);

    if (chunk.includes("[END]")) {
      const jsonPart = chunk.split("[END]")[1];
      onData({ type: "meta", data: JSON.parse(jsonPart) });
    } else {
      onData({ type: "text", data: chunk.replace("data: ", "") });
    }
  }
}
