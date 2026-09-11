/**
 * Bulle de chat de l'assistant Kalima.
 *
 * Injecte la bulle + le panneau dans la page, parle à /assistant/chat,
 * et appelle window.applyKalimaAction(action) quand le modèle détecte
 * une intention de configuration claire.
 *
 * IMPORTANT : window.applyKalimaAction doit être défini ailleurs dans
 * le frontend (dans le code qui connaît les vrais id/name des champs
 * du formulaire). Ce fichier ne remplit jamais un champ directement,
 * il se contente de proposer le réglage détecté — par sécurité et
 * pour rester découplé du HTML réel du formulaire.
 *
 * Exemple d'implémentation à fournir côté page principale :
 *
 *   window.applyKalimaAction = function (action) {
 *     if (action.mode) document.querySelector('#mode-select').value = action.mode;
 *     if (action.target_lang) document.querySelector('#target-lang').value = action.target_lang;
 *     if (action.source_lang) document.querySelector('#source-lang').value = action.source_lang;
 *     if (typeof action.clone_voice === 'boolean')
 *       document.querySelector('#clone-voice-checkbox').checked = action.clone_voice;
 *   };
 */

(function () {
  const history = [];

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (k === "text") node.textContent = v;
      else node.setAttribute(k, v);
    });
    (children || []).forEach((c) => node.appendChild(c));
    return node;
  }

  function buildWidget() {
    const bubble = el("div", { id: "kalima-assistant-bubble", text: "💬" });

    const panel = el("div", { id: "kalima-assistant-panel" }, [
      el("div", { id: "kalima-assistant-header", text: "Assistant Kalima" }),
      el("div", { id: "kalima-assistant-messages" }),
      el("div", { id: "kalima-assistant-input-row" }, [
        el("input", {
          id: "kalima-assistant-input",
          type: "text",
          placeholder: "Écris ta question…",
        }),
        el("button", { id: "kalima-assistant-send", text: "Envoyer" }),
      ]),
    ]);

    document.body.appendChild(bubble);
    document.body.appendChild(panel);

    bubble.addEventListener("click", () => panel.classList.toggle("open"));

    const input = panel.querySelector("#kalima-assistant-input");
    const sendBtn = panel.querySelector("#kalima-assistant-send");

    function send() {
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      sendMessage(text);
    }

    sendBtn.addEventListener("click", send);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") send();
    });

    // Message d'accueil, uniquement affiché (pas envoyé à l'historique modèle)
    appendMessage("assistant", "Salut 👋 Je suis l'assistant Kalima. Pose-moi une question, ou dis-moi directement ce que tu veux faire (ex: « traduis cette vidéo en anglais »).");
  }

  function appendMessage(role, text, pending) {
    const container = document.getElementById("kalima-assistant-messages");
    const msg = el("div", {
      class: `kalima-msg ${role}${pending ? " pending" : ""}`,
      text: text,
    });
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    return msg;
  }

  async function sendMessage(text) {
    appendMessage("user", text);
    history.push({ role: "user", content: text });

    const pendingMsg = appendMessage("assistant", "…", true);

    try {
      const res = await fetch("/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ history }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      pendingMsg.remove();
      appendMessage("assistant", data.reply);
      history.push({ role: "assistant", content: data.reply });

      if (data.action && typeof window.applyKalimaAction === "function") {
        window.applyKalimaAction(data.action);
      }
    } catch (err) {
      pendingMsg.remove();
      appendMessage(
        "assistant",
        "Désolé, je n'arrive pas à répondre pour le moment. Réessaie dans un instant."
      );
      console.error("Kalima assistant error:", err);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildWidget);
  } else {
    buildWidget();
  }
})();
