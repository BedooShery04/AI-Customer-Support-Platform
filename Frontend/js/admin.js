import {
  getDashboardStats,
  getTicketById,
  getTicketMessages,
  getUser,
  deleteTicket,
  changedTicketFields,
  deleteUser,
  getAgents,
  getTickets,
  getUsers,
  updateTicket,
  updateUser,
} from "./api.js";
import {
  ROLES,
  TICKET_CATEGORIES,
  TICKET_PRIORITIES,
  TICKET_STATUSES,
} from "./config.js";
import {
  accountBadge,
  escapeHTML,
  formatDate,
  openConfirmDialog,
  openDetailsDialog,
  priorityBadge,
  renderState,
  setButtonBusy,
  showToast,
  statusBadge,
} from "./ui.js";
import {
  calculateTicketStats,
  renderMessages,
  filterTickets,
  renderStatCards,
  renderTicketTable,
} from "./tickets.js";

const adminCards = [
  { key: "total", label: "Total Tickets", tone: "blue", icon: "▤" },
  { key: "open", label: "Open Tickets", tone: "amber", icon: "○" },
  { key: "inProgress", label: "In Progress", tone: "violet", icon: "◷" },
  { key: "resolved", label: "Resolved", tone: "green", icon: "✓" },
  { key: "critical", label: "Critical Tickets", tone: "red", icon: "!" },
];

function countBy(items, key, fallback = "Unassigned") {
  return items.reduce((result, item) => {
    const label = item[key] || fallback;
    result[label] = (result[label] || 0) + 1;
    return result;
  }, {});
}

function renderMiniBars(container, entries, total) {
  container.innerHTML = entries
    .map(([label, value]) => {
      const width = total ? Math.max(6, Math.round((value / total) * 100)) : 0;
      return `<div class="mini-bar-row"><div><span>${escapeHTML(label)}</span><strong>${value}</strong></div><div class="mini-bar"><span style="width:${width}%"></span></div></div>`;
    })
    .join("");
}

export async function initAdminDashboard() {
  const statsContainer = document.querySelector("#admin-stats");
  const recentContainer = document.querySelector("#admin-recent-tickets");
  const activityContainer = document.querySelector("#support-activity");
  const aiContainer = document.querySelector("#ai-activity");
  [statsContainer, recentContainer, activityContainer, aiContainer].forEach(element => renderState(element,"loading","Loading data..."));
  try {
    const dashboard = await getDashboardStats();
    const tickets = dashboard.recentTickets;
    renderStatCards(statsContainer, dashboard, adminCards);
    if (tickets.length) {
      renderTicketTable(recentContainer,tickets,{role:ROLES.ADMIN,showCustomer:true,showAgent:true,compact:true,
        actionRenderer: ticket => `<button class="table-link button-link" data-view-ticket="${ticket.id}">View</button>`});
      bindViewTicketButtons(recentContainer,tickets);
    } else { renderState(recentContainer,"empty","No tickets found"); }
    renderMiniBars(activityContainer,(dashboard.support_activity || []).map(a => [a.agent_name,a.assigned_tickets]),dashboard.total);
    const activity = dashboard.ai_activity || {};
    aiContainer.innerHTML = `<div class="activity-metric"><strong>${activity.classified_tickets || 0}</strong><span>Tickets classified</span></div>
      <div class="activity-metric"><strong>${activity.chat_requests || 0}</strong><span>Completed AI chats</span></div>
      <div class="activity-metric"><strong>${activity.suggestions || 0}</strong><span>Response suggestions generated</span></div>
      <p class="muted-note">Activity recorded by the backend during this server session.</p>`;
  } catch(error) {
    [statsContainer,recentContainer,activityContainer,aiContainer].forEach(element => renderState(element,"error","Unable to load dashboard",error.message));
  }
}

function userDetailsContent(user, extra = "") {
  return `<dl class="detail-grid">
    <div><dt>ID</dt><dd>${escapeHTML(user.id)}</dd></div>
    <div><dt>Name</dt><dd>${escapeHTML(user.name)}</dd></div>
    <div><dt>Email</dt><dd>${escapeHTML(user.email)}</dd></div>
    <div><dt>Role</dt><dd>${escapeHTML(user.role)}</dd></div>
    <div><dt>Created Date</dt><dd>${formatDate(user.createdAt, true)}</dd></div>
    <div><dt>Account Status</dt><dd>${accountBadge(user.status)}</dd></div>
    ${extra}
  </dl>`;
}

function renderUserTable(container, users, { agentCounts = null } = {}) {
  const isAgents = Boolean(agentCounts);
  container.innerHTML = `<div class="table-scroll"><table>
    <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>${
      isAgents ? "Account Status" : "Role"
    }</th>${isAgents ? "<th>Assigned Tickets</th>" : "<th>Created Date</th><th>Account Status</th>"}<th>Actions</th></tr></thead>
    <tbody>${users
      .map(
        (user) => `<tr>
          <td><strong class="ticket-id">${escapeHTML(user.id)}</strong></td>
          <td>${escapeHTML(user.name)}</td>
          <td>${escapeHTML(user.email)}</td>
          <td>${isAgents ? accountBadge(user.status) : escapeHTML(user.role)}</td>
          ${
            isAgents
              ? `<td>${agentCounts[user.id] || 0}</td>`
              : `<td>${formatDate(user.createdAt)}</td><td>${accountBadge(user.status)}</td>`
          }
          <td><div class="row-actions">
            <button class="table-link button-link" data-user-action="view" data-user-id="${user.id}">View</button>
            <button class="table-link button-link" data-user-action="toggle" data-user-id="${user.id}">${
              user.status === "Active" ? "Disable" : "Enable"
            }</button>
            <button class="table-link button-link table-link--danger" data-user-action="delete" data-user-id="${user.id}">Delete</button>
          </div></td>
        </tr>`,
      )
      .join("")}</tbody>
  </table></div>`;
}

async function bindUserActions(container, users, reload, agentCounts = null) {
  container.querySelectorAll("[data-user-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const user = users.find((item) => item.id === button.dataset.userId);
      if (!user) return;
      const action = button.dataset.userAction;
      if (action === "view") {
        const extra = agentCounts
          ? `<div><dt>Assigned Tickets</dt><dd>${agentCounts[user.id] || 0}</dd></div>`
          : "";
        setButtonBusy(button, true, "Loading...");
        try {
          const current = await getUser(user.id);
          openDetailsDialog({
            title: current.name,
            subtitle: current.email,
            content: userDetailsContent(current, extra),
          });
        } catch (error) {
          showToast(error.message || "Unable to load this account.", "error");
        } finally {
          setButtonBusy(button, false);
        }
        return;
      }
      if (action === "toggle") {
        const nextStatus = user.status === "Active" ? "Disabled" : "Active";
        const confirmed = await openConfirmDialog({
          title: `${nextStatus === "Active" ? "Enable" : "Disable"} account?`,
          message: `${user.name}'s account will be marked ${nextStatus.toLowerCase()}.`,
          confirmLabel: nextStatus === "Active" ? "Enable" : "Disable",
          danger: nextStatus === "Disabled",
        });
        if (!confirmed) return;
        try {
          await updateUser(user.id, { status: nextStatus });
          showToast(`Account ${nextStatus.toLowerCase()}.`);
          await reload();
        } catch (error) {
          showToast(error.message || "Unable to update the account.", "error");
        }
        return;
      }
      const confirmed = await openConfirmDialog({
        title: "Delete account?",
        message: `This deletes ${user.name}'s account and blocks login. Historical tickets remain; an agent's tickets become unassigned.`,
        confirmLabel: "Delete account",
        danger: true,
      });
      if (!confirmed) return;
      try {
        await deleteUser(user.id);
        showToast("Account deleted.");
        await reload();
      } catch (error) {
        showToast(error.message || "Unable to delete the account.", "error");
      }
    });
  });
}

export async function initAdminUsers() {
  const container = document.querySelector("#users-table");
  const count = document.querySelector("#users-count");
  const load = async () => {
    renderState(container, "loading", "Loading users…");
    try {
      const users = await getUsers(ROLES.CUSTOMER);
      count.textContent = `${users.length} customer account${users.length === 1 ? "" : "s"}`;
      if (!users.length) {
        renderState(container, "empty", "No users found");
        return;
      }
      renderUserTable(container, users);
      bindUserActions(container, users, load);
    } catch (error) {
      renderState(container, "error", "Unable to load users", error.message);
    }
  };
  await load();
}

export async function initAdminAgents() {
  const container = document.querySelector("#agents-table");
  const count = document.querySelector("#agents-count");
  const load = async () => {
    renderState(container, "loading", "Loading support agents…");
    try {
      const [agents, tickets] = await Promise.all([getAgents(), getTickets()]);
      const agentCounts = tickets.reduce((result, ticket) => {
        if (ticket.assignedAgentId) {
          result[ticket.assignedAgentId] = (result[ticket.assignedAgentId] || 0) + 1;
        }
        return result;
      }, {});
      count.textContent = `${agents.length} support agent${agents.length === 1 ? "" : "s"}`;
      if (!agents.length) {
        renderState(container, "empty", "No support agents found");
        return;
      }
      renderUserTable(container, agents, { agentCounts });
      bindUserActions(container, agents, load, agentCounts);
    } catch (error) {
      renderState(container, "error", "Unable to load support agents", error.message);
    }
  };
  await load();
}

function fillSelect(select, options, placeholder) {
  select.innerHTML = `<option value="">${placeholder}</option>${options
    .map((value) => `<option value="${escapeHTML(value)}">${escapeHTML(value)}</option>`)
    .join("")}`;
}

function ticketDetailsContent(ticket) {
  return `<div class="ticket-modal-summary"><div class="badge-group">${priorityBadge(
    ticket.priority,
  )}${statusBadge(ticket.status)}</div><p>${escapeHTML(ticket.description)}</p></div>
  <dl class="detail-grid detail-grid--three">
    <div><dt>Customer</dt><dd>${escapeHTML(ticket.customer?.name || "—")}</dd><small>${escapeHTML(
      ticket.customer?.email || "",
    )}</small></div>
    <div><dt>Category</dt><dd>${escapeHTML(ticket.category)}</dd></div>
    <div><dt>Assigned Agent</dt><dd>${escapeHTML(ticket.assignedAgent?.name || "Unassigned")}</dd></div>
    <div><dt>Created Date</dt><dd>${formatDate(ticket.createdAt, true)}</dd></div>
    <div><dt>Updated Date</dt><dd>${formatDate(ticket.updatedAt, true)}</dd></div>
  </dl>`;
}

function bindViewTicketButtons(container, tickets) {
  container.querySelectorAll("[data-view-ticket]").forEach(button => {
    button.addEventListener("click",async () => {
      setButtonBusy(button,true,"Loading...");
      try {
        const [ticket,messages] = await Promise.all([getTicketById(button.dataset.viewTicket),getTicketMessages(button.dataset.viewTicket)]);
        const conversation = document.createElement("div");
        renderMessages(conversation,messages);
        openDetailsDialog({ title:ticket.subject,subtitle:ticket.id,
          content:ticketDetailsContent(ticket)+`<h3>Conversation</h3><div class="ticket-conversation">${conversation.innerHTML}</div>` });
      } catch(error) { showToast(error.message,"error"); }
      finally { setButtonBusy(button,false); }
    });
  });
}

function openTicketManagement(ticket, agents, onSaved) {
  const dialog = document.createElement("dialog");
  dialog.className = "modal modal--wide";
  dialog.innerHTML = `<form class="modal-card" id="admin-ticket-form">
    <div class="modal-heading"><div><span class="ticket-id">${escapeHTML(
      ticket.id,
    )}</span><h2>${escapeHTML(ticket.subject)}</h2></div><button class="icon-button" type="button" data-close aria-label="Close">×</button></div>
    ${ticketDetailsContent(ticket)}
    <div class="form-grid form-grid--three">
      <label class="field"><span>Status</span><select name="status">${TICKET_STATUSES.map(
        (item) => `<option ${item === ticket.status ? "selected" : ""}>${item}</option>`,
      ).join("")}</select></label>
      <label class="field"><span>Priority</span><select name="priority">${TICKET_PRIORITIES.map(
        (item) => `<option ${item === ticket.priority ? "selected" : ""}>${item}</option>`,
      ).join("")}</select></label>
      <label class="field"><span>Assigned Agent</span><select name="assignedAgentId"><option value="">Unassigned</option>${agents
        .filter(agent => agent.status === "Active" || agent.id === ticket.assignedAgentId)
        .map(
          (agent) => `<option value="${agent.id}" ${
            agent.id === ticket.assignedAgentId ? "selected" : ""
          }>${escapeHTML(agent.name)}</option>`,
        )
        .join("")}</select></label>
    </div>
    <div class="form-alert hidden" data-form-message></div>
    <div class="modal-actions"><button class="button button--secondary" type="button" data-close>Cancel</button><button class="button button--primary" type="submit">Save changes</button></div>
  </form>`;
  document.body.append(dialog);
  dialog.querySelectorAll("[data-close]").forEach((button) =>
    button.addEventListener("click", () => dialog.close()),
  );
  const form = dialog.querySelector("form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type='submit']");
    const message = form.querySelector("[data-form-message]");
    message.className = "form-alert hidden";
    setButtonBusy(button, true, "Saving…");
    try {
      const changes = changedTicketFields(ticket, {
        status: form.elements.status.value,
        priority: form.elements.priority.value,
        assignedAgentId: form.elements.assignedAgentId.value || null,
      });
      if (!Object.keys(changes).length) {
        showToast("No changes to save.");
        return;
      }
      await updateTicket(ticket.id, changes);
      showToast("Ticket updated.");
      dialog.close();
      await onSaved();
    } catch (error) {
      message.className = "form-alert form-alert--error";
      message.textContent = error.message || "Unable to update the ticket.";
    } finally {
      setButtonBusy(button, false, "Saving…");
    }
  });
  dialog.addEventListener("close", () => dialog.remove());
  dialog.showModal();
}

export async function initAdminTickets() {
  const container = document.querySelector("#admin-tickets-table");
  const count = document.querySelector("#admin-ticket-count");
  const form = document.querySelector("#admin-ticket-filters");
  fillSelect(form.elements.status, TICKET_STATUSES, "All statuses");
  fillSelect(form.elements.priority, TICKET_PRIORITIES, "All priorities");
  fillSelect(form.elements.category, TICKET_CATEGORIES, "All categories");
  let tickets = [];
  let agents = [];

  const render = () => {
    const filtered = filterTickets(tickets, {
      status: form.elements.status.value,
      priority: form.elements.priority.value,
      category: form.elements.category.value,
      assignedAgentId: form.elements.assignedAgentId.value,
    });
    count.textContent = `${filtered.length} of ${tickets.length} tickets`;
    if (!filtered.length) {
      renderState(container, "empty", "No tickets found", "Try changing the selected filters.");
      return;
    }
    renderTicketTable(container, filtered, {
      role: ROLES.ADMIN,
      showCustomer: true,
      showAgent: true,
      actionRenderer: (ticket) =>
        `<div class="row-actions"><button class="table-link button-link" data-view-ticket="${ticket.id}">View</button><button class="table-link button-link" data-manage-ticket="${ticket.id}">Manage</button><button class="table-link button-link table-link--danger" data-delete-ticket="${ticket.id}">Delete</button></div>`,
    });
    bindViewTicketButtons(container, filtered);
    container.querySelectorAll("[data-delete-ticket]").forEach(button => button.addEventListener("click",async () => {
      const confirmed = await openConfirmDialog({title:"Delete ticket?",message:"This deletes the ticket and its conversation.",confirmLabel:"Delete ticket",danger:true});
      if (!confirmed) return;
      setButtonBusy(button,true,"Deleting...");
      try { await deleteTicket(button.dataset.deleteTicket); showToast("Ticket deleted."); await load(); }
      catch(error) { showToast(error.message,"error"); }
      finally { setButtonBusy(button,false); }
    }));
    container.querySelectorAll("[data-manage-ticket]").forEach((button) => {
      button.addEventListener("click", () => {
        const ticket = tickets.find((item) => item.id === button.dataset.manageTicket);
        if (ticket) openTicketManagement(ticket, agents, load);
      });
    });
  };

  const load = async () => {
    renderState(container, "loading", "Loading all tickets…");
    try {
      [tickets, agents] = await Promise.all([getTickets(), getAgents()]);
      form.elements.assignedAgentId.innerHTML = `<option value="">All assigned agents</option>${agents
        .map((agent) => `<option value="${agent.id}">${escapeHTML(agent.name)}</option>`)
        .join("")}`;
      render();
    } catch (error) {
      renderState(container, "error", "Unable to load tickets", error.message);
    }
  };
  form.addEventListener("change", render);
  form.addEventListener("reset", () => window.setTimeout(render));
  await load();
}

function renderBarChart(container, entries, total) {
  const max = Math.max(...entries.map(([, value]) => value), 1);
  container.innerHTML = `<div class="bar-chart">${entries
    .map(
      ([label, value]) => `<div class="bar-chart-row"><div class="bar-chart-label"><span>${escapeHTML(
        label,
      )}</span><strong>${value}</strong></div><div class="bar-track"><span style="width:${Math.round(
        (value / max) * 100,
      )}%"></span></div><small>${total ? Math.round((value / total) * 100) : 0}%</small></div>`,
    )
    .join("")}</div>`;
}

export async function initStatistics() {
  const stats = document.querySelector("#statistics-cards");
  const categories = document.querySelector("#category-chart");
  const statuses = document.querySelector("#status-chart");
  const agentsChart = document.querySelector("#agent-chart");
  const average = document.querySelector("#average-per-category");
  [stats,categories,statuses,agentsChart].forEach(element => renderState(element,"loading","Loading statistics..."));
  try {
    const dashboard = await getDashboardStats();
    renderStatCards(stats,dashboard,adminCards);
    renderBarChart(categories,Object.entries(dashboard.tickets_by_category || {}),dashboard.total);
    renderBarChart(statuses,Object.entries(dashboard.tickets_by_status || {}),dashboard.total);
    const agentCounts = (dashboard.support_activity || []).map(a => [a.agent_name,a.assigned_tickets]);
    const unassigned = dashboard.tickets_by_agent?.Unassigned || 0;
    if (unassigned) agentCounts.push(["Unassigned",unassigned]);
    renderBarChart(agentsChart,agentCounts,dashboard.total);
    average.textContent = Number(dashboard.average_tickets_per_category || 0).toFixed(1);
  } catch(error) {
    [stats,categories,statuses,agentsChart].forEach(element => renderState(element,"error","Unable to load statistics",error.message));
    average.textContent = "-";
  }
}
