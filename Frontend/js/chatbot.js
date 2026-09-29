
import {
    createChat,
    getChats,
    getChatMessages,
    renameChat,
    deleteChat,
    sendChatMessage,
} from "./api.js";

import {
    escapeHTML,
    formatDate,
    renderState,
    setButtonBusy,
} from "./ui.js";

import { registerPageTool } from "./webmcp.js";


function formatAIMessage(message) {
    let text = escapeHTML(String(message || ""));

    text = text.replace(
        /\\([*_`#-])/g,
        "$1"
    );

    text = text.replace(
        /\*\*(.+?)\*\*/g,
        "<strong>$1</strong>"
    );

    text = text.replace(
        /`([^`]+)`/g,
        "<code>$1</code>"
    );

    text = text.replace(
        /(^|\n)\s*-\s+(.+)/g,
        '$1<span class="ai-list-item">• $2</span>'
    );

    return text.replace(/\n/g, "<br>");
}


function renderChat(container, messages) {
    container.innerHTML = messages.map((item) => {
        const isAI =
            item.role === "ai" ||
            item.role === "assistant";

        return `
            <div class="chat-row chat-row--${isAI ? "ai" : "user"}">
                ${
                    isAI
                        ? `<div class="chat-avatar" aria-hidden="true">
                               <span></span>
                               <span></span>
                           </div>`
                        : ""
                }

                <div class="chat-message">
                    <div class="chat-message__label">
                        ${isAI ? "AI Assistant" : "You"}
                    </div>

                    <p>${
                        isAI
                            ? formatAIMessage(item.message)
                            : escapeHTML(item.message)
                    }</p>

                    <time>
                        ${item.timestamp
                            ? formatDate(item.timestamp, true)
                            : ""}
                    </time>
                </div>
            </div>
        `;
    }).join("");

    container.scrollTop = container.scrollHeight;
}


function appendTyping(container) {
    const row = document.createElement("div");

    row.className = "chat-row chat-row--ai";
    row.dataset.typing = "true";

    row.innerHTML = `
        <div class="chat-avatar">
            <span></span>
            <span></span>
        </div>

        <div
            class="chat-message chat-message--typing"
            aria-label="AI is typing"
        >
            <i></i>
            <i></i>
            <i></i>
        </div>
    `;

    container.append(row);
    container.scrollTop = container.scrollHeight;

    return row;
}


async function initializeAIChat({
    historySelector,
    formSelector,
    errorSelector,
    greetingSelector = null,
    user,
}) {
    const history = document.querySelector(historySelector);
    const form = document.querySelector(formSelector);
    const error = document.querySelector(errorSelector);

    if (!history || !form || !error) {
        return null;
    }

    const shell = history.closest(".chat-shell");

    if (!shell) {
        console.error("Chat shell not found.");
        return null;
    }

    const greeting = greetingSelector
        ? document.querySelector(greetingSelector)
        : null;

    if (greeting && user) {
        greeting.textContent =
            user.name.split(" ")[0];
    }

    // Build the sidebar for both customer and agent pages.
    const workspace = document.createElement("div");
    workspace.className = "ai-chat-workspace";

    const sidebar = document.createElement("aside");
    sidebar.className = "ai-chat-sidebar";

    sidebar.innerHTML = `
        <div class="ai-chat-sidebar__header">
            <h3>Chats</h3>

            <button
                type="button"
                class="button ai-new-chat"
                data-new-chat
            >
                + New Chat
            </button>
        </div>

        <p class="ai-chat-sidebar__label">
            Recent Chats
        </p>

        <div
            class="ai-chat-list"
            data-chat-list
        ></div>
    `;

    // Preserve the existing chat shell and its contents.
    shell.parentNode.insertBefore(
        workspace,
        shell
    );

    workspace.append(
        sidebar,
        shell
    );

    const chatList = sidebar.querySelector(
        "[data-chat-list]"
    );

    const newChatButton = sidebar.querySelector(
        "[data-new-chat]"
    );

    const submitButton = form.querySelector(
        'button[type="submit"]'
    );

    let chats = [];
    let activeChatId = null;
    let messages = [];

    let sending = false;
    let navigating = false;

    const showError = (message) => {
        error.textContent = message;
        error.classList.remove("hidden");
    };

    const clearError = () => {
        error.textContent = "";
        error.classList.add("hidden");
    };

    const setNavigationBusy = (busy) => {
        navigating = busy;
        newChatButton.disabled = busy || sending;

        chatList.querySelectorAll("button").forEach(
            (button) => {
                button.disabled = busy || sending;
            }
        );
    };

    function renderChatList() {
        chatList.innerHTML = "";

        if (!chats.length) {
            const empty = document.createElement("p");
            empty.className = "ai-chat-list__empty";
            empty.textContent = "No conversations yet.";

            chatList.append(empty);
            return;
        }

        chats.forEach((chat) => {
            const item = document.createElement("div");

            item.className = "ai-chat-list__item";

            if (chat.id === activeChatId) {
                item.classList.add(
                    "ai-chat-list__item--active"
                );
            }

            const openButton = document.createElement(
                "button"
            );

            openButton.type = "button";
            openButton.className = "ai-chat-list__open";
            openButton.textContent = chat.title;
            openButton.title = chat.title;

            openButton.addEventListener(
                "click",
                () => {
                    openChat(chat.id);
                }
            );

            const renameButton = document.createElement(
                "button"
            );

            renameButton.type = "button";
            renameButton.className =
                "ai-chat-list__action";

            renameButton.textContent = "✎";
            renameButton.title = "Rename chat";
            renameButton.setAttribute(
                "aria-label",
                `Rename ${chat.title}`
            );

            renameButton.addEventListener(
                "click",
                () => renameExistingChat(chat)
            );

            const deleteButton = document.createElement(
                "button"
            );

            deleteButton.type = "button";
            deleteButton.className =
                "ai-chat-list__action ai-chat-list__delete";

            deleteButton.textContent = "×";
            deleteButton.title = "Delete chat";
            deleteButton.setAttribute(
                "aria-label",
                `Delete ${chat.title}`
            );

            deleteButton.addEventListener(
                "click",
                () => deleteExistingChat(chat)
            );

            item.append(
                openButton,
                renameButton,
                deleteButton
            );

            chatList.append(item);
        });

        setNavigationBusy(navigating);
    }

    async function refreshChats() {
        chats = await getChats();
        renderChatList();
    }

    async function openChat(chatId) {
        if (sending || navigating) {
            return;
        }

        setNavigationBusy(true);
        clearError();

        renderState(
            history,
            "loading",
            "Loading conversation…"
        );

        try {
            const loadedMessages =
                await getChatMessages(chatId);

            activeChatId = chatId;
            messages = loadedMessages;

            renderChat(history, messages);
        } catch (loadError) {
            showError(
                loadError.message ||
                "Unable to load the conversation."
            );

            renderState(
                history,
                "error",
                "Unable to load the chat"
            );
        } finally {
            setNavigationBusy(false);
            renderChatList();
        }
    }

    async function startNewChat() {
        if (sending || navigating) {
            return;
        }

        setNavigationBusy(true);
        clearError();

        try {
            const chat = await createChat();

            chats.unshift(chat);

            activeChatId = chat.id;
            messages = [];

            renderChat(history, messages);
        } catch (createError) {
            showError(
                createError.message ||
                "Unable to create a new chat."
            );
        } finally {
            setNavigationBusy(false);
            renderChatList();
        }
    }

    async function renameExistingChat(chat) {
        if (sending || navigating) {
            return;
        }

        const title = window.prompt(
            "Enter a new chat name:",
            chat.title
        );

        if (title === null) {
            return;
        }

        const trimmedTitle = title.trim();

        if (!trimmedTitle) {
            showError("Chat name cannot be empty.");
            return;
        }

        if (trimmedTitle === chat.title) {
            return;
        }

        setNavigationBusy(true);
        clearError();

        try {
            await renameChat(
                chat.id,
                trimmedTitle
            );

            await refreshChats();
        } catch (renameError) {
            showError(renameError.message);
        } finally {
            setNavigationBusy(false);
            renderChatList();
        }
    }

    async function deleteExistingChat(chat) {
        if (sending || navigating) {
            return;
        }

        const confirmed = window.confirm(
            `Delete "${chat.title}" and all its messages?`
        );

        if (!confirmed) {
            return;
        }

        setNavigationBusy(true);
        clearError();

        try {
            await deleteChat(chat.id);

            chats = chats.filter(
                (item) => item.id !== chat.id
            );

            if (activeChatId === chat.id) {
                activeChatId = null;
                messages = [];

                renderChat(history, messages);
            }

            renderChatList();

            // Keep an existing chat selected if possible.
            if (
                activeChatId === null &&
                chats.length
            ) {
                const nextChat = chats[0];

                const loadedMessages =
                    await getChatMessages(nextChat.id);

                activeChatId = nextChat.id;
                messages = loadedMessages;

                renderChat(history, messages);
            }
        } catch (deleteError) {
            showError(
                deleteError.message ||
                "Unable to delete the chat."
            );
        } finally {
            setNavigationBusy(false);
            renderChatList();
        }
    }

    async function submitMessage(message) {
        const value = String(message || "").trim();

        if (!value) {
            throw new Error(
                "Write a message before sending."
            );
        }

        if (sending || navigating) {
            throw new Error(
                "The chat is currently busy."
            );
        }

        // Create a chat automatically if none is selected.
        if (activeChatId === null) {
            await startNewChat();

            if (activeChatId === null) {
                throw new Error(
                    "Unable to create a conversation."
                );
            }
        }

        sending = true;
        setNavigationBusy(false);
        submitButton.disabled = true;

        const chatId = activeChatId;
        const optimisticId = `local-${Date.now()}`;

        clearError();

        messages.push({
            id: optimisticId,
            role: "user",
            message: value,
            timestamp: new Date().toISOString(),
        });

        renderChat(history, messages);

        const typing = appendTyping(history);

        try {
            const reply = await sendChatMessage(
                chatId,
                value
            );

            typing.remove();

            // Reload persisted messages to get real IDs and dates.
            messages = await getChatMessages(chatId);

            renderChat(history, messages);

            await refreshChats();

            return reply;
        } catch (sendError) {
            typing.remove();

            // A request may have succeeded even if its
            // response was lost. Reload before retrying.
            try {
                messages = await getChatMessages(
                    chatId
                );
            } catch {
                messages = messages.filter(
                    (item) =>
                        item.id !== optimisticId
                );
            }

            renderChat(history, messages);

            showError(
                sendError.message ||
                "Unable to send the message."
            );

            throw sendError;
        } finally {
            sending = false;
            submitButton.disabled = false;
            setNavigationBusy(false);
            renderChatList();
        }
    }

    newChatButton.addEventListener(
        "click",
        startNewChat
    );

    form.addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            const input = form.elements.message;
            const value = input.value;

            if (!value.trim()) {
                showError(
                    "Write a message before sending."
                );

                input.focus();
                return;
            }

            if (sending || navigating) {
                return;
            }

            setButtonBusy(
                submitButton,
                true,
                "Sending…"
            );

            input.value = "";

            try {
                await submitMessage(value);
            } catch {
                // Restore text only if it was not saved.
                const wasSaved = messages.some(
                    (item) =>
                        item.role === "user" &&
                        item.message === value
                );

                if (!wasSaved) {
                    input.value = value;
                }
            } finally {
                setButtonBusy(
                    submitButton,
                    false,
                    "Sending…"
                );

                input.focus();
            }
        }
    );

    // Load previous chats on page initialization.
    renderState(
        history,
        "loading",
        "Loading conversations…"
    );

    try {
        await refreshChats();

        if (chats.length) {
            await openChat(chats[0].id);
        } else {
            renderChat(history, []);
        }
    } catch (loadError) {
        renderState(
            history,
            "error",
            "Unable to load conversations",
            loadError.message
        );

        showError(loadError.message);
    }

    return submitMessage;
}


export async function initChatbot(user) {
    const submitMessage = await initializeAIChat({
        historySelector: "#chat-history",
        formSelector: "#chat-form",
        errorSelector: "#chat-error",
        greetingSelector: "[data-chat-customer]",
        user,
    });

    if (!submitMessage) {
        return;
    }

    registerPageTool({
        name: "send_support_chat_message",
        title: "Message AI support",

        description:
            "Send one customer message to the AI support assistant and return its response.",

        inputSchema: {
            type: "object",

            properties: {
                message: {
                    type: "string",
                    minLength: 1,
                },
            },

            required: ["message"],
            additionalProperties: false,
        },

        annotations: {
            readOnlyHint: false,
            untrustedContentHint: true,
        },

        async execute(input) {
            const reply = await submitMessage(
                input.message
            );

            return {
                response: reply.message,
            };
        },
    });
}


export async function initAgentAIChat(user) {
    const submitMessage = await initializeAIChat({
        historySelector: "#agent-chat-history",
        formSelector: "#agent-chat-form",
        errorSelector: "#agent-chat-error",
        user,
    });

    if (!submitMessage) {
        return;
    }

    const createButton = document.querySelector(
        "#start-customer-ticket"
    );

    createButton?.addEventListener(
        "click",
        async () => {
            createButton.disabled = true;

            try {
                await submitMessage(
                    "I want to create a support ticket on behalf " +
                    "of a customer. Please ask me for the customer's " +
                    "email address and help me prepare a ticket draft."
                );
            } catch (error) {
                console.error(
                    "Unable to start ticket creation:",
                    error
                );
            } finally {
                createButton.disabled = false;
            }
        }
    );
}