
import {
    changedTicketFields,
    getDashboardStats,
    generateAIResponseSuggestion,
    classifyTicket,
    getTicketById,
    getTicketMessages,
    getTickets,
    sendTicketMessage,
    updateTicket,
    escalateTicket,
} from "./api.js";

import {
    TICKET_CATEGORIES,
    TICKET_PRIORITIES,
    TICKET_STATUSES,
} from "./config.js";

import {
    escapeHTML,
    formatDate,
    priorityBadge,
    renderState,
    setButtonBusy,
    showToast,
    statusBadge,
} from "./ui.js";

import {
    filterTickets,
    getQueryTicketId,
    renderMessages,
    renderStatCards,
    renderTicketTable,
} from "./tickets.js";

/* Dashboard */

const agentCards = [
    { key: "total", label: "Assigned Tickets", tone: "blue", icon: "▤" },
    { key: "open", label: "Open Tickets", tone: "amber", icon: "○" },
    { key: "inProgress", label: "In Progress", tone: "violet", icon: "◷" },
    { key: "resolved", label: "Resolved", tone: "green", icon: "✓" },
    { key: "critical", label: "Critical Tickets", tone: "red", icon: "!" },
];

export async function initAgentDashboard(user) {
    const statsContainer = document.querySelector("#agent-stats");
    const recentContainer = document.querySelector("#recent-assigned-tickets");
    const name = document.querySelector("[data-agent-name]");

    if (name) {
        name.textContent = user.name.split(" ")[0];
    }

    renderState(statsContainer, "loading", "Loading dashboard…");
    renderState(recentContainer, "loading", "Loading assigned tickets…");

    try {
        const dashboard = await getDashboardStats();
        const tickets = (await getTickets()).slice(0, 5);

        renderStatCards(statsContainer, dashboard, agentCards);

        if (!tickets.length) {
            renderState(
                recentContainer,
                "empty",
                "No assigned tickets",
                "Newly assigned tickets will appear here.",
            );
            return;
        }

        renderTicketTable(recentContainer, tickets, {
            role: user.role,
            showCustomer: true,
            showAgent: false,
            compact: true,
        });

    } catch (error) {
        renderState(
            statsContainer,
            "error",
            "Unable to load dashboard",
            error.message,
        );

        renderState(
            recentContainer,
            "error",
            "Unable to load tickets",
            "Please try again.",
        );
    }
}

/* Assigned Tickets */

function fillFilter(select, options, placeholder) {
    select.innerHTML = `
        <option value="">${placeholder}</option>
        ${options
            .map((option) => `
                <option value="${escapeHTML(option)}">
                    ${escapeHTML(option)}
                </option>
            `)
            .join("")}
    `;
}

export async function initAssignedTickets(user) {
    const container = document.querySelector("#assigned-tickets-table");
    const count = document.querySelector("#assigned-ticket-count");
    const form = document.querySelector("#ticket-filters");

    fillFilter(
        form.elements.status,
        TICKET_STATUSES,
        "All statuses",
    );

    fillFilter(
        form.elements.priority,
        TICKET_PRIORITIES,
        "All priorities",
    );

    fillFilter(
        form.elements.category,
        TICKET_CATEGORIES,
        "All categories",
    );

    renderState(container, "loading", "Loading assigned tickets…");

    try {
        const tickets = await getTickets();

        const render = () => {
            const filtered = filterTickets(tickets, {
                status: form.elements.status.value,
                priority: form.elements.priority.value,
                category: form.elements.category.value,
            });

            count.textContent =
                `${filtered.length} of ${tickets.length} tickets`;

            if (!filtered.length) {
                renderState(
                    container,
                    "empty",
                    "No tickets found",
                    "Try changing the selected filters.",
                );
                return;
            }

            renderTicketTable(container, filtered, {
                role: user.role,
                showCustomer: true,
                showAgent: false,
            });
        };

        form.addEventListener("change", render);

        form.addEventListener("reset", () => {
            window.setTimeout(render);
        });

        render();

    } catch (error) {
        renderState(
            container,
            "error",
            "Unable to load tickets",
            error.message,
        );
    }
}

/* Ticket Overview */

function renderAgentTicketOverview(container, ticket) {
    container.innerHTML = `
        <div class="ticket-heading-row">
            <div>
                <span class="ticket-id">
                    ${escapeHTML(ticket.id)}
                </span>

                <h2>${escapeHTML(ticket.subject)}</h2>
            </div>

            <div class="badge-group">
                ${priorityBadge(ticket.priority)}
                ${statusBadge(ticket.status)}
            </div>
        </div>

        <p class="ticket-description">
            ${escapeHTML(ticket.description)}
        </p>

        <dl class="detail-grid detail-grid--three">
            <div>
                <dt>Customer</dt>
                <dd>
                    ${escapeHTML(ticket.customer?.name || "—")}
                </dd>
                <small>
                    ${escapeHTML(ticket.customer?.email || "")}
                </small>
            </div>

            <div>
                <dt>Category</dt>
                <dd>${escapeHTML(ticket.category)}</dd>
            </div>

            <div>
                <dt>Assigned Agent</dt>
                <dd>
                    ${escapeHTML(
                        ticket.assignedAgent?.name || "Unassigned",
                    )}
                </dd>
            </div>

            <div>
                <dt>Created Date</dt>
                <dd>${formatDate(ticket.createdAt, true)}</dd>
            </div>

            <div>
                <dt>Updated Date</dt>
                <dd>${formatDate(ticket.updatedAt, true)}</dd>
            </div>
        </dl>
    `;
}

function optionList(options, selected) {
    return options
        .map((item) => `
            <option
                value="${escapeHTML(item)}"
                ${item === selected ? "selected" : ""}
            >
                ${escapeHTML(item)}
            </option>
        `)
        .join("");
}

/* Ticket Conversation */

async function refreshConversation(ticketId, container) {
    const messages = await getTicketMessages(ticketId);
    renderMessages(container, messages);
}

function bindMessageForm(form, ticketId, conversation) {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const textarea = form.elements.message;
        const error = form.querySelector(
            "[data-error-for='message']",
        );

        const value = textarea.value.trim();

        error.textContent = "";

        if (!value) {
            error.textContent = "Write a reply before sending.";
            textarea.focus();
            return;
        }

        const button = form.querySelector(
            "button[type='submit']",
        );

        setButtonBusy(button, true, "Sending…");

        try {
            await sendTicketMessage(ticketId, value);

            textarea.value = "";

            await refreshConversation(ticketId, conversation);

            showToast("Reply sent to the customer.");

        } catch (errorMessage) {
            error.textContent =
                errorMessage.message ||
                "Unable to send the reply.";

        } finally {
            setButtonBusy(button, false, "Send Reply");
        }
    });
}

/* AI Response Suggestion */

function bindAISuggestion(ticketId, conversation) {
    const generate = document.querySelector(
        "#generate-suggestion",
    );

    const panel = document.querySelector(
        "#suggestion-panel",
    );

    const textarea = document.querySelector(
        "#ai-suggestion-text",
    );

    const send = document.querySelector(
        "#send-suggestion",
    );

    const error = document.querySelector(
        "#suggestion-error",
    );

    const generateSuggestion = async () => {
        error.classList.add("hidden");

        setButtonBusy(generate, true, "Generating…");

        try {
            const result =
                await generateAIResponseSuggestion(ticketId);

            textarea.value = result.suggestion;

            panel.classList.remove("hidden");

            generate.textContent = "Regenerate suggestion";
            generate.dataset.label = "Regenerate suggestion";

            textarea.focus();

        } catch (requestError) {
            error.textContent =
                requestError.message ||
                "Unable to generate a suggestion.";

            error.classList.remove("hidden");

        } finally {
            setButtonBusy(
                generate,
                false,
                generate.dataset.label || "Generate AI Suggestion",
            );
        }
    };

    generate.addEventListener(
        "click",
        generateSuggestion,
    );

    send.addEventListener("click", async () => {
        const response = textarea.value.trim();

        error.classList.add("hidden");

        if (!response) {
            error.textContent =
                "Review and enter a response before sending.";

            error.classList.remove("hidden");
            textarea.focus();
            return;
        }

        setButtonBusy(send, true, "Sending…");

        try {
            await sendTicketMessage(ticketId, response);

            textarea.value = "";

            panel.classList.add("hidden");

            await refreshConversation(
                ticketId,
                conversation,
            );

            showToast(
                "AI-assisted response sent after your confirmation.",
            );

        } catch (sendError) {
            error.textContent =
                sendError.message ||
                "Unable to send the response.";

            error.classList.remove("hidden");

        } finally {
            setButtonBusy(send, false, "Send Response");
        }
    });
}

/* AI Classification */

function bindAIClassification(
    ticketId,
    existingClassification = null,
) {
    const classify = document.querySelector(
        "#classify-ticket",
    );

    const reclassify = document.querySelector(
        "#reclassify-ticket",
    );

    const emptyPanel = document.querySelector(
        "#classification-empty",
    );

    const panel = document.querySelector(
        "#classification-panel",
    );

    const error = document.querySelector(
        "#classification-error",
    );

    const category = document.querySelector(
        "#ai-classification-category",
    );

    const priority = document.querySelector(
        "#ai-classification-priority",
    );

    const summary = document.querySelector(
        "#ai-classification-summary",
    );

    const action = document.querySelector(
        "#ai-classification-action",
    );

    if (!classify) {
        return;
    }

    const renderClassification = (result) => {
        category.textContent =
            result?.category || "—";

        priority.textContent =
            result?.priority || "—";

        summary.textContent =
            result?.summary || "—";

        action.textContent =
            result?.suggestedAction ||
            result?.suggested_action ||
            "—";

        emptyPanel.classList.add("hidden");
        panel.classList.remove("hidden");
    };

    const runClassification = async (button) => {
        error.classList.add("hidden");

        setButtonBusy(button, true, "Analyzing…");

        try {
            const result = await classifyTicket(ticketId);

            renderClassification(result);

            showToast(
                "Ticket classified successfully.",
            );

        } catch (requestError) {
            error.textContent =
                requestError.message ||
                "Unable to classify the ticket.";

            error.classList.remove("hidden");

        } finally {
            setButtonBusy(
                button,
                false,
                button === classify
                    ? "Classify Ticket with AI"
                    : "Reclassify with AI",
            );
        }
    };

    classify.addEventListener("click", () => {
        runClassification(classify);
    });

    reclassify?.addEventListener("click", () => {
        runClassification(reclassify);
    });

    if (existingClassification) {
        renderClassification(existingClassification);
    }
}

/* Agent Ticket Details */

export async function initAgentTicketDetails() {
    const ticketId = getQueryTicketId();

    const overview = document.querySelector(
        "#agent-ticket-overview",
    );

    const conversation = document.querySelector(
        "#ticket-conversation",
    );

    const controls = document.querySelector(
        "#ticket-controls",
    );

    const messageForm = document.querySelector(
        "#agent-message-form",
    );

    if (!ticketId) {
        renderState(
            overview,
            "error",
            "Ticket not selected",
            "Return to Assigned Tickets and choose one.",
        );

        controls?.remove();
        messageForm?.remove();

        return;
    }

    renderState(
        overview,
        "loading",
        "Loading ticket…",
    );

    renderState(
        conversation,
        "loading",
        "Loading conversation…",
    );

    try {
        const [ticket, messages] = await Promise.all([
            getTicketById(ticketId),
            getTicketMessages(ticketId),
        ]);

        renderAgentTicketOverview(overview, ticket);
        renderMessages(conversation, messages);

        controls.elements.status.innerHTML = optionList(
            TICKET_STATUSES,
            ticket.status,
        );

        controls.elements.priority.innerHTML = optionList(
            TICKET_PRIORITIES,
            ticket.priority,
        );

        /* Save Ticket Changes */

        controls.addEventListener(
            "submit",
            async (event) => {
                event.preventDefault();

                const button = controls.querySelector(
                    "button[type='submit']",
                );

                setButtonBusy(
                    button,
                    true,
                    "Saving…",
                );

                try {
                    const changes = changedTicketFields(
                        ticket,
                        {
                            status:
                                controls.elements.status.value,

                            priority:
                                controls.elements.priority.value,
                        },
                    );

                    if (!Object.keys(changes).length) {
                        showToast("No changes to save.");
                        return;
                    }

                    await updateTicket(
                        ticketId,
                        changes,
                    );

                    showToast(
                        "Ticket updated successfully.",
                    );

                    window.location.reload();

                } catch (updateError) {
                    showToast(
                        updateError.message ||
                        "Unable to update the ticket.",
                        "error",
                    );

                } finally {
                    setButtonBusy(
                        button,
                        false,
                        "Save Changes",
                    );
                }
            },
        );

        /* Escalate Ticket */

        const escalateButton = document.querySelector(
            "#escalate-ticket",
        );

        escalateButton?.addEventListener(
            "click",
            async () => {
                setButtonBusy(
                    escalateButton,
                    true,
                    "Escalating…",
                );

                try {
                    await escalateTicket(ticketId);

                    showToast(
                        "Ticket escalated successfully.",
                    );

                    window.location.reload();

                } catch (error) {
                    showToast(
                        error.message ||
                        "Unable to escalate the ticket.",
                        "error",
                    );

                } finally {
                    setButtonBusy(
                        escalateButton,
                        false,
                        "Escalate Ticket",
                    );
                }
            },
        );

        /* Bind Remaining Features */

        bindMessageForm(
            messageForm,
            ticketId,
            conversation,
        );

        bindAISuggestion(
            ticketId,
            conversation,
        );

        bindAIClassification(
            ticketId,
            ticket.aiClassification ??
            ticket.ai_classification,
        );

    } catch (error) {
        renderState(
            overview,
            "error",
            "Unable to load ticket",
            error.message,
        );

        renderState(
            conversation,
            "error",
            "Unable to load conversation",
            "Please try again.",
        );

        controls?.remove();
        messageForm?.remove();

        document.querySelector(
            "#ai-suggestion-card",
        )?.remove();

        document.querySelector(
            "#ai-classification-card",
        )?.remove();
    }
}

/* Agent Customers */

export async function initAgentCustomers() {
    const container = document.querySelector(
        "#agent-customers",
    );

    if (!container) {
        return;
    }

    renderState(
        container,
        "loading",
        "Loading customers…",
    );

    try {
        const tickets = await getTickets();

        if (!tickets.length) {
            renderState(
                container,
                "empty",
                "No customers yet",
                "Customers with assigned tickets will appear here.",
            );
            return;
        }

        const customers = new Map();

        tickets.forEach((ticket) => {
            const customer = ticket.customer;

            if (!customer?.id) {
                return;
            }

            if (!customers.has(customer.id)) {
                customers.set(customer.id, {
                    ...customer,
                    tickets: [],
                });
            }

            customers.get(customer.id).tickets.push(
                ticket,
            );
        });

        if (!customers.size) {
            renderState(
                container,
                "empty",
                "No customer information available",
                "Customer information could not be loaded.",
            );
            return;
        }

        container.innerHTML = Array.from(
            customers.values(),
        )
            .map((customer) => {
                const customerTickets = customer.tickets;

                const open = customerTickets.filter(
                    (ticket) => ticket.status === "Open",
                ).length;

                const inProgress = customerTickets.filter(
                    (ticket) =>
                        ticket.status === "In Progress",
                ).length;

                const waiting = customerTickets.filter(
                    (ticket) =>
                        ticket.status ===
                        "Waiting for Customer",
                ).length;

                const resolved = customerTickets.filter(
                    (ticket) =>
                        ticket.status === "Resolved",
                ).length;

                return `
                    <article class="customer-card">

                        <div class="customer-card__header">
                            <div>
                                <h2>
                                    ${escapeHTML(
                                        customer.name || "—",
                                    )}
                                </h2>

                                <p>
                                    ${escapeHTML(
                                        customer.email || "—",
                                    )}
                                </p>
                            </div>

                            <span class="customer-ticket-count">
                                ${customerTickets.length}
                                ${
                                    customerTickets.length === 1
                                        ? "Ticket"
                                        : "Tickets"
                                }
                            </span>
                        </div>

                        <div class="customer-ticket-stats">
                            <span>Open: ${open}</span>

                            <span>
                                In Progress: ${inProgress}
                            </span>

                            <span>Waiting: ${waiting}</span>

                            <span>Resolved: ${resolved}</span>
                        </div>

                        <div class="customer-card__footer">
                            <a
                                class="button button--secondary"
                                href="/agent/customer-details.html?id=${
                                    encodeURIComponent(customer.id)
                                }"
                            >
                                View Customer
                            </a>
                        </div>

                    </article>
                `;
            })
            .join("");

    } catch (error) {
        renderState(
            container,
            "error",
            "Unable to load customers",
            error.message,
        );
    }
}

/* Agent Customer Details */

export async function initAgentCustomerDetails(user) {
    const nameElement = document.querySelector(
        "#customer-name",
    );

    const emailElement = document.querySelector(
        "#customer-email",
    );

    const statsContainer = document.querySelector(
        "#customer-stats",
    );

    const ticketsContainer = document.querySelector(
        "#customer-tickets",
    );

    const customerId = new URLSearchParams(
        window.location.search,
    ).get("id");

    if (!customerId) {
        renderState(
            ticketsContainer,
            "error",
            "Customer not selected",
            "Return to Customers and select a customer.",
        );
        return;
    }

    renderState(
        ticketsContainer,
        "loading",
        "Loading customer tickets...",
    );

    try {
        const allTickets = await getTickets();

        const tickets = allTickets.filter(
            (ticket) =>
                String(
                    ticket.customerId ??
                    ticket.customer_id,
                ) === String(customerId),
        );

        if (!tickets.length) {
            nameElement.textContent =
                "Customer not found";

            emailElement.textContent = "";

            renderState(
                ticketsContainer,
                "empty",
                "No tickets found",
                "No assigned tickets were found for this customer.",
            );

            return;
        }

        const customer = tickets[0].customer;

        document.querySelector(
            "#customer-info-name",
        ).textContent = customer?.name || "—";

        document.querySelector(
            "#customer-info-email",
        ).textContent = customer?.email || "—";

        document.querySelector(
            "#customer-info-id",
        ).textContent = customer?.id ?? customerId;

        nameElement.textContent =
            customer?.name || "Customer";

        emailElement.textContent =
            customer?.email || "—";

        const countStatus = (status) =>
            tickets.filter(
                (ticket) => ticket.status === status,
            ).length;

        const stats = [
            ["Total Tickets", tickets.length],
            ["Open", countStatus("Open")],
            ["In Progress", countStatus("In Progress")],
            [
                "Waiting",
                countStatus("Waiting for Customer"),
            ],
            ["Resolved", countStatus("Resolved")],
        ];

        statsContainer.innerHTML = stats
            .map(
                ([label, value]) => `
                    <div class="customer-stat-card">
                        <span>${escapeHTML(label)}</span>
                        <strong>${value}</strong>
                    </div>
                `,
            )
            .join("");

        renderTicketTable(
            ticketsContainer,
            tickets,
            {
                role: user.role,
                showCustomer: false,
                showAgent: false,
            },
        );

    } catch (error) {
        renderState(
            ticketsContainer,
            "error",
            "Unable to load customer",
            error.message,
        );
    }
}