import {
  getDashboardStats,
  createTicket,
  getTicketById,
  getTicketMessages,
  getTickets,
  sendTicketMessage,
} from "./api.js";
import {
  TICKET_CATEGORIES,
  TICKET_PRIORITIES,
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
  getQueryTicketId,
  renderMessages,
  renderStatCards,
  renderTicketTable,
} from "./tickets.js";
import { registerPageTool } from "./webmcp.js";

function customerCards() {
  return [
    { key: "total", label: "Total Tickets", tone: "blue", icon: "▤" },
    { key: "open", label: "Open Tickets", tone: "amber", icon: "○" },
    { key: "inProgress", label: "In Progress", tone: "violet", icon: "◷" },
    { key: "resolved", label: "Resolved", tone: "green", icon: "✓" },
  ];
}

export async function initCustomerDashboard(user) {
  const statsContainer = document.querySelector("#customer-stats");
  const recentContainer = document.querySelector("#recent-tickets");
  const name = document.querySelector("[data-customer-name]");
  if (name) name.textContent = user.name.split(" ")[0];
  renderState(statsContainer, "loading", "Loading dashboard…");
  renderState(recentContainer, "loading", "Loading recent tickets…");
  try {
    const dashboard = await getDashboardStats();
    const tickets = dashboard.recentTickets;
    renderStatCards(statsContainer, dashboard, customerCards());
    if (!tickets.length) {
      renderState(
        recentContainer,
        "empty",
        "No tickets yet",
        "Create your first support ticket when you need help.",
      );
      return;
    }
    renderTicketTable(recentContainer, tickets.slice(0, 4), {
      role: user.role,
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

export async function initCustomerTickets(user) {
  const container = document.querySelector("#tickets-table");
  const count = document.querySelector("#ticket-count");
  renderState(container, "loading", "Loading tickets…");
  try {
    const tickets = await getTickets();
    if (count) count.textContent = `${tickets.length} ticket${tickets.length === 1 ? "" : "s"}`;
    if (!tickets.length) {
      renderState(
        container,
        "empty",
        "No tickets found",
        "Create a ticket to start a support request.",
      );
      return;
    }
    renderTicketTable(container, tickets, { role: user.role, showAgent: true });
  } catch (error) {
    renderState(container, "error", "Unable to load tickets", error.message);
  }
}

function setCreateFormError(form, field, message = "") {
  const element = form.querySelector(`[data-error-for="${field}"]`);
  if (element) element.textContent = message;
  form.elements[field]?.setAttribute("aria-invalid", String(Boolean(message)));
}

function validateTicketPayload(payload) {
  const errors = {};
  if (payload.subject.length < 5) errors.subject = "Use at least 5 characters.";
  if (payload.description.length < 15) {
    errors.description = "Describe the issue using at least 15 characters.";
  }
  if (!TICKET_CATEGORIES.includes(payload.category)) {
    errors.category = "Choose a valid category.";
  }
  if (!TICKET_PRIORITIES.includes(payload.priority)) {
    errors.priority = "Choose a valid priority.";
  }
  return errors;
}

async function submitTicketPayload(payload, { form, button, redirect = true } = {}) {
  const errors = validateTicketPayload(payload);
  if (Object.keys(errors).length) {
    if (form) {
      Object.entries(errors).forEach(([field, message]) =>
        setCreateFormError(form, field, message),
      );
    }
    throw new Error(Object.values(errors)[0]);
  }
  setButtonBusy(button, true, "Creating ticket…");
  try {
    const ticket = await createTicket(payload);
    if (form) {
      const message = form.querySelector("[data-form-message]");
      message.className = "form-alert form-alert--success";
      message.textContent = `${ticket.id} was created successfully.`;
      form.reset();
    }
    showToast("Ticket created successfully.");
    if (redirect) {
      window.setTimeout(() => {
        window.location.href = `/customer/ticket-details.html?id=${encodeURIComponent(ticket.id)}`;
      }, 500);
    }
    return ticket;
  } finally {
    setButtonBusy(button, false, "Creating ticket…");
  }
}

export function initCreateTicket() {
  const form = document.querySelector("#create-ticket-form");
  const category = form?.elements.category;
  const priority = form?.elements.priority;
  if (category) {
    category.innerHTML = `<option value="">Select a category</option>${TICKET_CATEGORIES.map(
      (item) => `<option value="${item}">${item}</option>`,
    ).join("")}`;
  }
  if (priority) {
    priority.innerHTML = `<option value="">Select a priority</option>${TICKET_PRIORITIES.map(
      (item) => `<option value="${item}">${item}</option>`,
    ).join("")}`;
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    form.querySelectorAll("[data-error-for]").forEach((element) => {
      element.textContent = "";
    });
    form.querySelectorAll("[aria-invalid]").forEach((element) =>
      element.setAttribute("aria-invalid", "false"),
    );
    const message = form.querySelector("[data-form-message]");
    message.className = "form-alert hidden";
    const payload = {
      subject: form.elements.subject.value.trim(),
      description: form.elements.description.value.trim(),
      category: form.elements.category.value,
      priority: form.elements.priority.value,
    };
    try {
      await submitTicketPayload(payload, {
        form,
        button: form.querySelector("button[type='submit']"),
      });
    } catch (error) {
      message.className = "form-alert form-alert--error";
      message.textContent = error.message || "Unable to create the ticket.";
    }
  });

  registerPageTool({
    name: "create_support_ticket",
    title: "Create support ticket",
    description:
      "Create a customer support ticket and return the created ticket identifier.",
    inputSchema: {
      type: "object",
      properties: {
        subject: { type: "string", minLength: 5 },
        description: { type: "string", minLength: 15 },
        category: { type: "string", enum: TICKET_CATEGORIES },
        priority: { type: "string", enum: TICKET_PRIORITIES },
      },
      required: ["subject", "description", "category", "priority"],
      additionalProperties: false,
    },
    annotations: { readOnlyHint: false, untrustedContentHint: false },
    async execute(input) {
      const ticket = await submitTicketPayload(
        {
          subject: String(input.subject || "").trim(),
          description: String(input.description || "").trim(),
          category: input.category,
          priority: input.priority,
        },
        { redirect: false },
      );
      return { ticketId: ticket.id, status: ticket.status };
    },
  });
}

function renderTicketOverview(container, ticket) {
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
    <dl class="detail-grid">
      <div><dt>Category</dt><dd>${escapeHTML(ticket.category)}</dd></div>
      <div><dt>Assigned Support Agent</dt><dd>${escapeHTML(
        ticket.assignedAgent?.name || "Not assigned yet",
      )}</dd></div>
      <div><dt>Created Date</dt><dd>${formatDate(ticket.createdAt, true)}</dd></div>
      <div><dt>Updated Date</dt><dd>${formatDate(ticket.updatedAt, true)}</dd></div>
    </dl>`;
}

function renderAIClassification(container, classification) {
  if (!container) return;
  if (!classification) {
    container.closest(".content-card")?.remove();
    return;
  }
  container.innerHTML = `
    <div class="ai-insight">
      <div><span>AI Short Summary</span><p>${escapeHTML(classification.summary)}</p></div>
      <div><span>AI Suggested Action</span><p>${escapeHTML(
        classification.suggestedAction,
      )}</p></div>
    </div>`;
}

export async function initCustomerTicketDetails() {
  const ticketId = getQueryTicketId();
  const overview = document.querySelector("#ticket-overview");
  const conversation = document.querySelector("#ticket-conversation");
  const ai = document.querySelector("#ai-classification");
  const form = document.querySelector("#message-form");
  if (!ticketId) {
    renderState(overview, "error", "Ticket not selected", "Return to My Tickets and choose one.");
    form?.remove();
    return;
  }
  renderState(overview, "loading", "Loading ticket…");
  renderState(conversation, "loading", "Loading conversation…");
  try {
    const [ticket, messages] = await Promise.all([
      getTicketById(ticketId),
      getTicketMessages(ticketId),
    ]);
    renderTicketOverview(overview, ticket);
    renderAIClassification(ai, ticket.aiClassification);
    renderMessages(conversation, messages);

    form?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const textarea = form.elements.message;
      const error = form.querySelector("[data-error-for='message']");
      const value = textarea.value.trim();
      error.textContent = "";
      if (!value) {
        error.textContent = "Write a message before sending.";
        textarea.focus();
        return;
      }
      const button = form.querySelector("button[type='submit']");
      setButtonBusy(button, true, "Sending…");
      try {
        await sendTicketMessage(ticketId, value);
        textarea.value = "";
        renderMessages(conversation, await getTicketMessages(ticketId));
        showToast("Message sent.");
      } catch (sendError) {
        error.textContent = sendError.message || "Unable to send the message.";
      } finally {
        setButtonBusy(button, false, "Sending…");
      }
    });
  } catch (error) {
    renderState(overview, "error", "Unable to load ticket", error.message);
    renderState(conversation, "error", "Unable to load conversation", "Please try again.");
    form?.remove();
  }
}
