// Amorae web chat — POST a message, stream the reply over SSE.
// EventSource is GET-only, so we use fetch + a manual `data:` parser.
(function () {
  const root = document.querySelector(".chat");
  const bot = root.dataset.bot;
  const list = document.getElementById("messages");
  const form = document.getElementById("composer");
  const input = document.getElementById("input");

  function addMsg(role, text) {
    const el = document.createElement("div");
    el.className = "msg " + role;
    el.textContent = text;
    list.appendChild(el);
    list.scrollTop = list.scrollHeight;
    return el;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    addMsg("user", text);
    const replyEl = addMsg("assistant", "");

    let resp;
    try {
      resp = await fetch(`/${bot}/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ content: text }),
      });
    } catch (err) {
      replyEl.textContent = "…couldn't reach me just now. try again?";
      return;
    }
    if (!resp.ok || !resp.body) {
      replyEl.textContent = "…couldn't reach me just now. try again?";
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop();
      for (const frame of frames) {
        const line = frame.trim();
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (payload === "[DONE]") return;
        try {
          const obj = JSON.parse(payload);
          if (obj.delta) {
            replyEl.textContent += obj.delta;
            list.scrollTop = list.scrollHeight;
          } else if (obj.error) {
            replyEl.textContent = "…something went wrong. try again?";
          }
        } catch (_) {}
      }
    }
  });
})();
