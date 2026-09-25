import {
  changedTicketFields,
  getDashboardStats,
  generateAIResponseSuggestion,
  getAgents,
  getTicketById,
  getTicketMessages,
  getTickets,
  sendTicketMessage,
  updateTicket,
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
  calculateTicketStats,
  filterTickets,
  getQueryTicketId,
  renderMessages,
  renderStatCards,
  renderTicketTable,
} from "./tickets.js";

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
  if (name) name.textContent = user.name.split(" ")[0];
  renderState(statsContainer, "loading", "Loading dashboard…");
  renderState(recentContainer, "loading", "Loading assigned tickets…");
  try {
    const dashboard = await getDashboardStats();
    const tickets = dashboard.recentTickets;
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
    renderTicketTable(recentContainer, tickets.slice(0, 5), {
      role: user.role,
      showCustomer: true,
      showAgent: false,
      compact: true,
    });
  } catch (error) {
    renderState(statsContainer, "error", "Unable to load dashboard", error.message);
    renderState(recentContainer, "error", "Unable to load tickets", "Please try again.");
  }
}

function fillFilter(select, options, placeholder) {
  select.innerHTML = `<option value="">${placeholder}</option>${options
    .map((option) => `<option value="${option}">${option}</option>`)
    .join("")}`;
}

export async function initAssignedTickets(user) {
  const container = document.querySelector("#assigned-tickets-table");
  const count = document.querySelector("#assigned-ticket-count");
  const form = document.querySelector("#ticket-filters");
  fillFilter(form.elements.status, TICKET_STATUSES, "All statuses");
  fillFilter(form.elements.priority, TICKET_PRIORITIES, "All priorities");
  fillFilter(form.elements.category, TICKET_CATEGORIES, "All categories");
  renderState(container, "loading", "Loading assigned tickets…");
  try {
    const tickets = await getTickets();
    const render = () => {
      const filtered = filterTickets(tickets, {
        status: form.elements.status.value,
        priority: form.elements.priority.value,
        category: form.elements.category.value,
      });
      count.textContent = `${filtered.length} of ${tickets.length} tickets`;
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
    form.addEventListener("reset", () => window.setTimeout(render));
    render();
  } catch (error) {
    renderState(container, "error", "Unable to load tickets", error.message);
  }
}

function renderAgentTicketOverview(container, ticket) {
  container.innerHTML = `
    <div class="ticket-heading-row">
      <div><span class="ticket-id">${escapeHTML(ticket.id)}</span><h2>${escapeHTML(
        ticket.subject,
      )}</h2></div>
      <div class="badge-group">${priorityBadge(ticket.priority)}${statusBadge(
        ticket.status,
      )}</div>
    </div>
    <p class="ticket-description">${escapeHTML(ticket.description)}</p>
    <dl class="detail-grid detail-grid--three">
      <div><dt>Customer</dt><dd>${escapeHTML(ticket.customer?.name || "—")}</dd><small>${escapeHTML(
        ticket.customer?.email || "",
      )}</small></div>
      <div><dt>Category</dt><dd>${escapeHTML(ticket.category)}</dd></div>
      <div><dt>Assigned Agent</dt><dd>${escapeHTML(
        ticket.assignedAgent?.name || "Unassigned",
      )}</dd></div>
      <div><dt>Created Date</dt><dd>${formatDate(ticket.createdAt, true)}</dd></div>
      <div><dt>Updated Date</dt><dd>${formatDate(ticket.updatedAt, true)}</dd></div>
    </dl>`;
}

function optionList(options, selected) {
  return options
    .map(
      (item) =>
        `<option value="${escapeHTML(item)}" ${item === selected ? "selected" : ""}>${escapeHTML(
          item,
        )}</option>`,
    )
    .join("");
}

async function refreshConversation(ticketId, container) {
  const messages = await getTicketMessages(ticketId);
  renderMessages(container, messages);
}

function bindMessageForm(form, ticketId, conversation) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const textarea = form.elements.message;
    const error = form.querySelector("[data-error-for='message']");
    const value = textarea.value.trim();
    error.textContent = "";
    if (!value) {
      error.textContent = "Write a reply before sending.";
      textarea.focus();
      return;
    }
    const button = form.querySelector("button[type='submit']");
    setButtonBusy(button, true, "Sending…");
    try {
      await sendTicketMessage(ticketId, value);
      textarea.value = "";
      await refreshConversation(ticketId, conversation);
      showToast("Reply sent to the customer.");
    } catch (errorMessage) {
      error.textContent = errorMessage.message || "Unable to send the reply.";
    } finally {
      setButtonBusy(button, false, "Sending…");
    }
  });
}

function bindAISuggestion(ticketId, conversation) {
  const generate = document.querySelector("#generate-suggestion");
  const panel = document.querySelector("#suggestion-panel");
  const textarea = document.querySelector("#ai-suggestion-text");
  const send = document.querySelector("#send-suggestion");
  const error = document.querySelector("#suggestion-error");

  const generateSuggestion = async () => {
    error.classList.add("hidden");
    setButtonBusy(generate, true, "Generating…");
    try {
      const result = await generateAIResponseSuggestion(ticketId);
      textarea.value = result.suggestion;
      panel.classList.remove("hidden");
      generate.textContent = "Regenerate suggestion";
      generate.dataset.label = "Regenerate suggestion";
      textarea.focus();
    } catch (requestError) {
      error.textContent = requestError.message || "Unable to generate a suggestion.";
      error.classList.remove("hidden");
    } finally {
      setButtonBusy(generate, false, "Generating…");
    }
  };

  generate.addEventListener("click", generateSuggestion);
  send.addEventListener("click", async () => {
    const response = textarea.value.trim();
    error.classList.add("hidden");
    if (!response) {
      error.textContent = "Review and enter a response before sending.";
      error.classList.remove("hidden");
      textarea.focus();
      return;
    }
    setButtonBusy(send, true, "Sending…");
    try {
      await sendTicketMessage(ticketId, response);
      textarea.value = "";
      panel.classList.add("hidden");
      await refreshConversation(ticketId, conversation);
      showToast("AI-assisted response sent after your confirmation.");
    } catch (sendError) {
      error.textContent = sendError.message || "Unable to send the response.";
      error.classList.remove("hidden");
    } finally {
      setButtonBusy(send, false, "Sending…");
    }
  });
}

export async function initAgentTicketDetails() {
  const ticketId = getQueryTicketId();
  const overview = document.querySelector("#agent-ticket-overview");
  const conversation = document.querySelector("#ticket-conversation");
  const controls = document.querySelector("#ticket-controls");
  const messageForm = document.querySelector("#agent-message-form");
  if (!ticketId) {
    renderState(overview, "error", "Ticket not selected", "Return to Assigned Tickets and choose one.");
    controls?.remove();
    messageForm?.remove();
    return;
  }
  renderState(overview, "loading", "Loading ticket…");
  renderState(conversation, "loading", "Loading conversation…");
  try {
    const [ticket, messages, agents] = await Promise.all([
      getTicketById(ticketId),
      getTicketMessages(ticketId),
      getAgents(),
    ]);
    renderAgentTicketOverview(overview, ticket);
    renderMessages(conversation, messages);

    controls.elements.status.innerHTML = optionList(TICKET_STATUSES, ticket.status);
    controls.elements.priority.innerHTML = optionList(TICKET_PRIORITIES, ticket.priority);
    controls.elements.assignedAgentId.innerHTML = `<option value="">Unassigned</option>${agents
      .map(
        (agent) =>
          `<option value="${agent.id}" ${
            agent.id === ticket.assignedAgentId ? "selected" : ""
          }>${escapeHTML(agent.name)}</option>`,
      )
      .join("")}`;

    controls.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = controls.querySelector("button[type='submit']");
      setButtonBusy(button, true, "Saving…");
      try {
        const changes = changedTicketFields(ticket, {
          status: controls.elements.status.value,
          priority: controls.elements.priority.value,
          assignedAgentId: controls.elements.assignedAgentId.value || null,
        });
        if (!Object.keys(changes).length) {
          showToast("No changes to save.");
          return;
        }
        const updated = await updateTicket(ticketId, changes);
        showToast("Ticket controls updated.");
        if (updated.assignedAgentId !== ticket.assignedAgentId) {
          window.setTimeout(() => window.location.replace("/agent/assigned-tickets.html"), 450);
        } else {
          window.location.reload();
        }
      } catch (updateError) {
        showToast(updateError.message || "Unable to update the ticket.", "error");
      } finally {
        setButtonBusy(button, false, "Saving…");
      }
    });

    bindMessageForm(messageForm, ticketId, conversation);
    bindAISuggestion(ticketId, conversation);
  } catch (error) {
    renderState(overview, "error", "Unable to load ticket", error.message);
    renderState(conversation, "error", "Unable to load conversation", "Please try again.");
    controls?.remove();
    messageForm?.remove();
    document.querySelector("#ai-suggestion-card")?.remove();
  }
}
