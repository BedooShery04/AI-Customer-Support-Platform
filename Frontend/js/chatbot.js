import {getChatMessages, sendChatMessage} from "./api.js";
import {escapeHTML, formatDate, renderState, setButtonBusy} from "./ui.js";
import {registerPageTool} from "./webmcp.js";

function renderChat(container, messages) {
    container.innerHTML = messages
        .map(
        (item) => `<div class="chat-row chat-row--${item.role}">
            ${
            item.role === "ai"
                ? '<div class="chat-avatar" aria-hidden="true"><span></span><span></span></div>'
                : ""
            }
            <div class="chat-message"><div class="chat-message__label">${
            item.role === "ai" ? "AI Assistant" : "You"
            }</div><p>${escapeHTML(item.message)}</p><time>${formatDate(
            item.timestamp,
            true,
            )}</time></div>
        </div>`,
        )
        .join("");
    container.scrollTop = container.scrollHeight;
}

function appendTyping(container) {
    const row = document.createElement("div");
    row.className = "chat-row chat-row--ai";
    row.dataset.typing = "true";
    row.innerHTML = `<div class="chat-avatar"><span></span><span></span></div><div class="chat-message chat-message--typing" aria-label="AI is typing"><i></i><i></i><i></i></div>`;
    container.append(row);
    container.scrollTop = container.scrollHeight;
    return row;
}

export async function initChatbot(user) {
    const history = document.querySelector("#chat-history");
    const form = document.querySelector("#chat-form");
    const error = document.querySelector("#chat-error");
    const greeting = document.querySelector("[data-chat-customer]");
    if (greeting) greeting.textContent = user.name.split(" ")[0];
    renderState(history, "loading", "Loading conversation…");
    let messages = [];
    let sending = false;
    try {
        messages = await getChatMessages();
        renderChat(history, messages);
    } catch (loadError) {
        renderState(history, "error", "Unable to load the chat", loadError.message);
    }

    async function submitMessage(message) {
        const value = String(message || "").trim();
        if (!value) throw new Error("Write a message before sending.");
        if (sending) throw new Error("A message is already being sent.");
        sending = true;
        const optimisticId = `local-${Date.now()}`;
        error.classList.add("hidden");
        messages.push({
        id: optimisticId,
        role: "user",
        message: value,
        timestamp: new Date().toISOString(),
        });
        renderChat(history, messages);
        const typing = appendTyping(history);
        try {
        const reply = await sendChatMessage(value);
        messages.push(reply);
        typing.remove();
        renderChat(history, messages);
        return reply;
        } catch (sendError) {
        typing.remove();
        messages = messages.filter(item => item.id !== optimisticId);
        renderChat(history, messages);
        error.textContent = sendError.message || "The AI assistant is unavailable. Please try again.";
        error.classList.remove("hidden");
        throw sendError;
        } finally { sending = false; }
    }

    form?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const input = form.elements.message;
        const value = input.value;
        if (!value.trim()) {
        error.textContent = "Write a message before sending.";
        error.classList.remove("hidden");
        input.focus();
        return;
        }
        const button = form.querySelector("button[type='submit']");
        setButtonBusy(button, true, "Sending…");
        input.value = "";
        try {
        await submitMessage(value);
        } catch {
        input.value = value;
        } finally {
        setButtonBusy(button, false, "Sending…");
        input.focus();
        }
    });

    registerPageTool({
        name: "send_support_chat_message",
        title: "Message AI support",
        description:
        "Send one customer message to the AI support assistant and return its response.",
        inputSchema: {
        type: "object",
        properties: { message: { type: "string", minLength: 1 } },
        required: ["message"],
        additionalProperties: false,
        },
        annotations: { readOnlyHint: false, untrustedContentHint: true },
        async execute(input) {
        const reply = await submitMessage(input.message);
        return { response: reply.message };
        },
    });
}
