import { escapeHTML, formatDate, priorityBadge, statusBadge } from "./ui.js";

export function calculateTicketStats(tickets) {
    return {
        total: tickets.length,
        open: tickets.filter((ticket) => ticket.status === "Open").length,
        inProgress: tickets.filter((ticket) => ticket.status === "In Progress").length,
        resolved: tickets.filter((ticket) => ticket.status === "Resolved").length,
        critical: tickets.filter((ticket) => ticket.priority === "Critical").length,
    };
}

export function renderStatCards(container, stats, cards) {
    if (!container) return;
    container.innerHTML = cards
        .map(
        ({ key, label, tone = "blue", icon = "●" }) => `
        <article class="stat-card">
            <div class="stat-icon stat-icon--${tone}" aria-hidden="true">${icon}</div>
            <div><span>${escapeHTML(label)}</span><strong>${stats[key] ?? 0}</strong></div>
        </article>`,
        )
        .join("");
}

export function ticketDetailsPath(role, ticketId) {
    const id = encodeURIComponent(ticketId);

    if (role === "customer") {
        return new URL(
            `../customer/ticket-details.html?id=${id}`,
            import.meta.url
        ).href;
    }

    if (role === "agent") {
        return new URL(
            `../agent/ticket-details.html?id=${id}`,
            import.meta.url
        ).href;
    }

    return "#";
}
export function renderTicketTable(
    container,
    tickets,
    { role, showCustomer = false, showAgent = true, compact = false, actionRenderer } = {},
    ) {
    if (!container) return;
    const header = [
        "Ticket",
        ...(showCustomer ? ["Customer"] : []),
        "Subject",
        ...(compact ? [] : ["Category"]),
        "Priority",
        "Status",
        ...(showAgent ? ["Assigned Agent"] : []),
        "Created",
        ...(compact ? [] : ["Updated"]),
        "",
    ];

    const rows = tickets
        .map((ticket) => {
        const action = actionRenderer
            ? actionRenderer(ticket)
            : `<a class="table-link" href="${ticketDetailsPath(role, ticket.id)}">View</a>`;
        return `<tr>
            <td><strong class="ticket-id">${escapeHTML(ticket.id)}</strong></td>
            ${showCustomer ? `<td>${escapeHTML(ticket.customer?.name || "—")}</td>` : ""}
            <td><span class="table-subject">${escapeHTML(ticket.subject)}</span></td>
            ${compact ? "" : `<td>${escapeHTML(ticket.category)}</td>`}
            <td>${priorityBadge(ticket.priority)}</td>
            <td>${statusBadge(ticket.status)}</td>
            ${showAgent ? `<td>${escapeHTML(ticket.assignedAgent?.name || "Unassigned")}</td>` : ""}
            <td>${formatDate(ticket.createdAt)}</td>
            ${compact ? "" : `<td>${formatDate(ticket.updatedAt)}</td>`}
            <td class="table-actions">${action}</td>
        </tr>`;
        })
        .join("");

    container.innerHTML = `<div class="table-scroll"><table>
        <thead><tr>${header.map((label) => `<th>${label}</th>`).join("")}</tr></thead>
        <tbody>${rows}</tbody>
    </table></div>`;
}

export function renderMessages(container, messages) {
    if (!container) return;
    if (!messages.length) {
        container.innerHTML = `<div class="conversation-empty"><span>○</span><strong>No messages yet</strong><p>Start the conversation below.</p></div>`;
        return;
    }
    container.innerHTML = messages
        .map(
        (item) => `<article class="message message--${
            item.senderRole === "customer" ? "customer" : "agent"
        }">
            <div class="message-meta"><strong>${escapeHTML(item.senderName)}</strong><span>${
            item.senderRole === "customer" ? "Customer" : "Support Agent"
            } · ${formatDate(item.timestamp, true)}</span></div>
            <p>${escapeHTML(item.message)}</p>
        </article>`,
        )
        .join("");
    container.scrollTop = container.scrollHeight;
}

export function getQueryTicketId() {
    return new URLSearchParams(window.location.search).get("id");
}

export function filterTickets(tickets, filters) {
    return tickets.filter((ticket) =>
        Object.entries(filters).every(([key, value]) => {
            if (!value) return true;

            if (key === "assignedAgentId") {
                return String(ticket[key] ?? "") === String(value);
            }

            return ticket[key] === value;
        })
    );
}