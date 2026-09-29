
import {
    createChat,
    getChats,
    getChatMessages,
    getChatPendingOperation,
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


/* =========================
   Message Formatting
========================= */

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


/* =========================
   Chat Messages
========================= */

function renderChat(container, messages) {
    container.innerHTML = messages.map(item => {
        const isAI =
            item.role === "ai" ||
            item.role === "assistant";

        return `
            <div class="chat-row chat-row--${isAI ? "ai" : "user"}">
                ${
                    isAI
                        ? `
                            <div
                                class="chat-avatar"
                                aria-hidden="true"
                            >
                                <span></span>
                                <span></span>
                            </div>
                        `
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
                        ${
                            item.timestamp
                                ? formatDate(
                                    item.timestamp,
                                    true
                                )
                                : ""
                        }
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


/* =========================
   Pending Draft Formatting
========================= */

function renderCreationDraft(operation) {
    const tickets = operation.tickets || [];

    const customer = operation.customer
        ? `
            <div class="ai-draft-customer">
                <span class="ai-draft-field-label">
                    Creating tickets on behalf of
                </span>

                <strong>
                    ${escapeHTML(operation.customer.name)}
                </strong>

                <span>
                    ${escapeHTML(operation.customer.email)}
                </span>
            </div>
        `
        : "";

    return `
        ${customer}

        <div class="ai-draft-tickets">
            ${tickets.map((ticket, index) => `
                <section class="ai-draft-ticket">
                    <span class="ai-draft-ticket-number">
                        Ticket ${index + 1}
                    </span>

                    <div class="ai-draft-field">
                        <span class="ai-draft-field-label">
                            Subject
                        </span>

                        <strong>
                            ${escapeHTML(ticket.subject)}
                        </strong>
                    </div>

                    <div class="ai-draft-field">
                        <span class="ai-draft-field-label">
                            Description
                        </span>

                        <p>
                            ${escapeHTML(ticket.description)}
                        </p>
                    </div>
                </section>
            `).join("")}
        </div>

        <p class="ai-draft-note">
            ${
                tickets.length === 1
                    ? "This ticket has not been created yet."
                    : "These tickets have not been created yet."
            }
        </p>
    `;
}


function renderUpdateDraft(operation) {
    const renderChange = (
        label,
        currentValue,
        proposedValue
    ) => {
        if (proposedValue == null) {
            return "";
        }

        return `
            <div class="ai-draft-change">
                <strong>${label}</strong>

                <div class="ai-draft-change__field">
                    <span class="ai-draft-field-label">
                        Current
                    </span>

                    <p>
                        ${escapeHTML(currentValue ?? "—")}
                    </p>
                </div>

                <div class="ai-draft-change__field">
                    <span class="ai-draft-field-label">
                        Proposed
                    </span>

                    <p class="ai-draft-proposed">
                        ${escapeHTML(proposedValue)}
                    </p>
                </div>
            </div>
        `;
    };

    return `
        <div class="ai-draft-ticket-reference">
            Ticket #${escapeHTML(operation.ticketId)}
        </div>

        <div class="ai-draft-changes">
            ${renderChange(
                "Subject",
                operation.currentSubject,
                operation.newSubject
            )}

            ${renderChange(
                "Description",
                operation.currentDescription,
                operation.newDescription
            )}
        </div>

        <p class="ai-draft-note">
            These changes have not been applied yet.
        </p>
    `;
}


/* =========================
   Pending Draft Card
========================= */

function renderPendingDraft(
    container,
    operation,
    {
        onConfirm,
        onCancel,
        busy = false,
    } = {}
) {
    container.innerHTML = "";

    if (!operation) {
        container.classList.add("hidden");
        return;
    }

    const isCreation =
        operation.type === "ticket_creation";

    const isUpdate =
        operation.type === "ticket_update";

    if (!isCreation && !isUpdate) {
        container.classList.add("hidden");
        return;
    }

    container.classList.remove("hidden");

    const title = isCreation
        ? "Review proposed tickets"
        : "Review ticket changes";

    const content = isCreation
        ? renderCreationDraft(operation)
        : renderUpdateDraft(operation);

    const expiresAt = operation.expiresAt
        ? formatDate(operation.expiresAt, true)
        : null;

    container.innerHTML = `
        <div class="ai-draft-card">
            <div class="ai-draft-header">
                <div>
                    <span class="ai-draft-eyebrow">
                        ${
                            isCreation
                                ? "AI Ticket Draft"
                                : "AI Ticket Update"
                        }
                    </span>

                    <h3>
                        ${title}
                    </h3>
                </div>

                <span class="ai-draft-badge">
                    Pending
                </span>
            </div>

            ${content}

            ${
                expiresAt
                    ? `
                        <p class="ai-draft-expiry">
                            Expires: ${escapeHTML(expiresAt)}
                        </p>
                    `
                    : ""
            }

            <div class="ai-draft-actions">
                <button
                    type="button"
                    class="button button--primary"
                    data-draft-confirm
                    ${busy ? "disabled" : ""}
                >
                    Confirm
                </button>

                <button
                    type="button"
                    class="button button--secondary"
                    data-draft-cancel
                    ${busy ? "disabled" : ""}
                >
                    Cancel
                </button>
            </div>
        </div>
    `;

    container
        .querySelector("[data-draft-confirm]")
        .addEventListener("click", () => {
            onConfirm?.();
        });

    container
        .querySelector("[data-draft-cancel]")
        .addEventListener("click", () => {
            onCancel?.();
        });
}


/* =========================
   Initialize AI Chat
========================= */

async function initializeAIChat({
    historySelector,
    formSelector,
    errorSelector,
    greetingSelector = null,
    user,
}) {
    const history = document.querySelector(
        historySelector
    );

    const form = document.querySelector(
        formSelector
    );

    const error = document.querySelector(
        errorSelector
    );

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


    /* =========================
       Build Workspace
    ========================= */

    const workspace =
        document.createElement("div");

    workspace.className =
        "ai-chat-workspace";

    const sidebar =
        document.createElement("aside");

    sidebar.className =
        "ai-chat-sidebar";

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

    shell.parentNode.insertBefore(
        workspace,
        shell
    );

    workspace.append(
        sidebar,
        shell
    );


    /* =========================
       Pending Draft Container
    ========================= */

    const draftContainer =
        document.createElement("div");

    draftContainer.className =
        "ai-draft-container hidden";

    // Place the draft above the message composer.
    const composer =
        shell.querySelector(".chat-composer");

    if (composer) {
        shell.insertBefore(
            draftContainer,
            composer
        );
    } else {
        history.insertAdjacentElement(
            "afterend",
            draftContainer
        );
    }


    /* =========================
       Elements and State
    ========================= */

    const chatList = sidebar.querySelector(
        "[data-chat-list]"
    );

    const newChatButton =
        sidebar.querySelector(
            "[data-new-chat]"
        );

    const submitButton =
        form.querySelector(
            'button[type="submit"]'
        );

    let chats = [];

    let activeChatId = null;

    let messages = [];

    let pendingOperation = null;

    let sending = false;

    let navigating = false;


    /* =========================
       Error Handling
    ========================= */

    const showError = message => {
        error.textContent = message;
        error.classList.remove("hidden");
    };

    const clearError = () => {
        error.textContent = "";
        error.classList.add("hidden");
    };


    /* =========================
       Navigation State
    ========================= */

    const setNavigationBusy = busy => {
        navigating = busy;

        newChatButton.disabled =
            busy || sending;

        chatList
            .querySelectorAll("button")
            .forEach(button => {
                button.disabled =
                    busy || sending;
            });
    };


    /* =========================
       Draft State
    ========================= */

    function renderCurrentDraft() {
        renderPendingDraft(
            draftContainer,
            pendingOperation,
            {
                busy: sending || navigating,

                onConfirm: () =>
                    submitDraftAction("Confirm"),

                onCancel: () =>
                    submitDraftAction("Cancel"),
            }
        );
    }


    async function refreshPendingOperation(
        chatId = activeChatId
    ) {
        if (chatId == null) {
            pendingOperation = null;
            renderCurrentDraft();
            return;
        }

        const result =
            await getChatPendingOperation(chatId);

        // Ignore responses from a chat that is no
        // longer selected.
        if (activeChatId !== chatId) {
            return;
        }

        pendingOperation =
            result.pendingOperation;

        renderCurrentDraft();
    }


    async function submitDraftAction(command) {
        if (
            sending ||
            navigating ||
            !pendingOperation
        ) {
            return;
        }

        const chatId = activeChatId;

        // Prevent duplicate confirmation requests.
        sending = true;
        setNavigationBusy(false);
        submitButton.disabled = true;
        renderCurrentDraft();

        sending = false;

        try {
            // submitMessage manages the sending state,
            // message history, and draft refresh.
            await submitMessage(command);
        } catch (actionError) {
            showError(
                actionError.message ||
                "Unable to process the draft."
            );
        }

        // Do not update a different chat if navigation
        // becomes possible after the request.
        if (activeChatId === chatId) {
            renderCurrentDraft();
        }
    }


    /* =========================
       Chat List
    ========================= */

    function renderChatList() {
        chatList.innerHTML = "";

        if (!chats.length) {
            const empty =
                document.createElement("p");

            empty.className =
                "ai-chat-list__empty";

            empty.textContent =
                "No conversations yet.";

            chatList.append(empty);
            return;
        }

        chats.forEach(chat => {
            const item =
                document.createElement("div");

            item.className =
                "ai-chat-list__item";

            if (chat.id === activeChatId) {
                item.classList.add(
                    "ai-chat-list__item--active"
                );
            }

            const openButton =
                document.createElement("button");

            openButton.type = "button";

            openButton.className =
                "ai-chat-list__open";

            openButton.textContent =
                chat.title;

            openButton.title =
                chat.title;

            openButton.addEventListener(
                "click",
                () => openChat(chat.id)
            );

            const renameButton =
                document.createElement("button");

            renameButton.type = "button";

            renameButton.className =
                "ai-chat-list__action";

            renameButton.textContent = "✎";

            renameButton.title =
                "Rename chat";

            renameButton.setAttribute(
                "aria-label",
                `Rename ${chat.title}`
            );

            renameButton.addEventListener(
                "click",
                () => renameExistingChat(chat)
            );

            const deleteButton =
                document.createElement("button");

            deleteButton.type = "button";

            deleteButton.className =
                "ai-chat-list__action ai-chat-list__delete";

            deleteButton.textContent = "×";

            deleteButton.title =
                "Delete chat";

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


    /* =========================
       Open Chat
    ========================= */

    async function openChat(chatId) {
        if (sending || navigating) {
            return;
        }

        setNavigationBusy(true);
        clearError();

        pendingOperation = null;
        renderCurrentDraft();

        renderState(
            history,
            "loading",
            "Loading conversation…"
        );

        try {
            const [
                loadedMessages,
                draftResult,
            ] = await Promise.all([
                getChatMessages(chatId),
                getChatPendingOperation(chatId),
            ]);

            activeChatId = chatId;

            messages = loadedMessages;

            pendingOperation =
                draftResult.pendingOperation;

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
            renderCurrentDraft();
        }
    }


    /* =========================
       Create Chat
    ========================= */

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

            pendingOperation = null;

            renderChat(history, messages);
            renderCurrentDraft();
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


    /* =========================
       Rename Chat
    ========================= */

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

        const trimmedTitle =
            title.trim();

        if (!trimmedTitle) {
            showError(
                "Chat name cannot be empty."
            );
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


    /* =========================
       Delete Chat
    ========================= */

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
                item => item.id !== chat.id
            );

            if (activeChatId === chat.id) {
                activeChatId = null;

                messages = [];

                pendingOperation = null;

                renderChat(history, messages);
                renderCurrentDraft();
            }

            if (
                activeChatId === null &&
                chats.length
            ) {
                const nextChat = chats[0];

                const [
                    loadedMessages,
                    draftResult,
                ] = await Promise.all([
                    getChatMessages(nextChat.id),
                    getChatPendingOperation(
                        nextChat.id
                    ),
                ]);

                activeChatId =
                    nextChat.id;

                messages =
                    loadedMessages;

                pendingOperation =
                    draftResult.pendingOperation;

                renderChat(
                    history,
                    messages
                );

                renderCurrentDraft();
            }
        } catch (deleteError) {
            showError(
                deleteError.message ||
                "Unable to delete the chat."
            );
        } finally {
            setNavigationBusy(false);
            renderChatList();
            renderCurrentDraft();
        }
    }


    /* =========================
       Send Message
    ========================= */

    async function submitMessage(message) {
        const value =
            String(message || "").trim();

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

        renderCurrentDraft();

        const chatId =
            activeChatId;

        const optimisticId =
            `local-${Date.now()}`;

        clearError();

        messages.push({
            id: optimisticId,
            role: "user",
            message: value,
            timestamp:
                new Date().toISOString(),
        });

        renderChat(
            history,
            messages
        );

        const typing =
            appendTyping(history);

        try {
            const reply =
                await sendChatMessage(
                    chatId,
                    value
                );

            typing.remove();

            // Reload persisted messages and the
            // current pending operation.
            const [
                loadedMessages,
                draftResult,
            ] = await Promise.all([
                getChatMessages(chatId),
                getChatPendingOperation(
                    chatId
                ),
            ]);

            messages =
                loadedMessages;

            pendingOperation =
                draftResult.pendingOperation;

            renderChat(
                history,
                messages
            );

            renderCurrentDraft();

            try {
                await refreshChats();
            } catch (refreshError) {
                console.error(
                    "Unable to refresh chats:",
                    refreshError
                );
            }

            return reply;
        } catch (sendError) {
            typing.remove();

            // Reload persisted state because the
            // request may have completed on the server.
            try {
                const [
                    loadedMessages,
                    draftResult,
                ] = await Promise.all([
                    getChatMessages(chatId),
                    getChatPendingOperation(
                        chatId
                    ),
                ]);

                messages =
                    loadedMessages;

                pendingOperation =
                    draftResult.pendingOperation;
            } catch {
                messages = messages.filter(
                    item =>
                        item.id !== optimisticId
                );

                // Do not show potentially stale actions.
                pendingOperation = null;
            }

            renderChat(
                history,
                messages
            );

            renderCurrentDraft();

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
            renderCurrentDraft();
        }
    }


    /* =========================
       Event Listeners
    ========================= */

    newChatButton.addEventListener(
        "click",
        startNewChat
    );

    form.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            const input =
                form.elements.message;

            const value =
                input.value;

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
                const wasSaved =
                    messages.some(
                        item =>
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


    /* =========================
       Initial Load
    ========================= */

    renderState(
        history,
        "loading",
        "Loading conversations…"
    );

    try {
        await refreshChats();

        if (chats.length) {
            await openChat(
                chats[0].id
            );
        } else {
            renderChat(history, []);
            renderCurrentDraft();
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


/* =========================
   Customer Chat
========================= */

export async function initChatbot(user) {
    const submitMessage =
        await initializeAIChat({
            historySelector:
                "#chat-history",

            formSelector:
                "#chat-form",

            errorSelector:
                "#chat-error",

            greetingSelector:
                "[data-chat-customer]",

            user,
        });

    if (!submitMessage) {
        return;
    }

    registerPageTool({
        name:
            "send_support_chat_message",

        title:
            "Message AI support",

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
            const reply =
                await submitMessage(
                    input.message
                );

            return {
                response: reply.message,
            };
        },
    });
}


/* =========================
   Agent Chat
========================= */

export async function initAgentAIChat(user) {
    const submitMessage =
        await initializeAIChat({
            historySelector:
                "#agent-chat-history",

            formSelector:
                "#agent-chat-form",

            errorSelector:
                "#agent-chat-error",

            user,
        });

    if (!submitMessage) {
        return;
    }

    const createButton =
        document.querySelector(
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