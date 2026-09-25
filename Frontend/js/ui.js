import {ROLES} from "./config.js";
import {logout} from "./auth.js";

const icons = {
    dashboard:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 13h6V4H4v9Zm0 7h6v-5H4v5Zm10 0h6v-9h-6v9Zm0-16v5h6V4h-6Z"/></svg>',
    ticket:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12a2 2 0 0 0 0-4V5H4v3a2 2 0 0 0 0 4 2 2 0 0 0 0 4v3h16v-3a2 2 0 0 0 0-4Z"/><path d="M9 8v8"/></svg>',
    plus:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
    chat:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12a8 8 0 0 1-8 8H5l-3 2 1-5a9 9 0 1 1 18-5Z"/></svg>',
    users:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    agent:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 13v-2a8 8 0 0 1 16 0v2M18 19h-2v-6h4v4a2 2 0 0 1-2 2ZM6 19H4a2 2 0 0 1-2-2v-4h4v6ZM12 19h4"/></svg>',
    chart:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
    logout:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 17l5-5-5-5M15 12H3M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/></svg>',
    menu:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg>',
    arrow:
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>',
};

const navigation = {
    [ROLES.CUSTOMER]: [
        ["dashboard", "Dashboard", "/customer/dashboard.html", "dashboard"],
        ["tickets", "My Tickets", "/customer/tickets.html", "ticket"],
        ["create-ticket", "Create Ticket", "/customer/create-ticket.html", "plus"],
        ["chatbot", "AI Chatbot", "/customer/chatbot.html", "chat"],
    ],
    [ROLES.AGENT]: [
        ["dashboard", "Dashboard", "/agent/dashboard.html", "dashboard"],
        ["assigned-tickets", "Assigned Tickets", "/agent/assigned-tickets.html", "ticket"],
    ],
    [ROLES.ADMIN]: [
        ["dashboard", "Dashboard", "/admin/dashboard.html", "dashboard"],
        ["users", "Users", "/admin/users.html", "users"],
        ["agents", "Agents", "/admin/agents.html", "agent"],
        ["tickets", "Tickets", "/admin/tickets.html", "ticket"],
        ["statistics", "Statistics", "/admin/statistics.html", "chart"],
    ],
};

const roleLabels = {
    CUSTOMER: "Customer",
    AGENT: "Support Agent",
    ADMIN: "Administrator",
};

export function escapeHTML(value = "") {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

export function formatDate(value, includeTime = false) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat("en", {
        month: "short",
        day: "numeric",
        year: "numeric",
        ...(includeTime ? { hour: "numeric", minute: "2-digit" } : {}),
    }).format(date);
}

export function initials(name = "") {
    return name
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0])
        .join("")
        .toUpperCase();
}

function navItem([page, label, href, icon], currentPage) {
    const active = page === currentPage;
    return `<a class="nav-link${active ? " is-active" : ""}" href="${href}" ${
        active ? 'aria-current="page"' : ""
    }>${icons[icon]}<span>${label}</span></a>`;
}

export function createAppShell({ user, role, currentPage, title, eyebrow }) {
    const main = document.querySelector("#page-content");
    if (!main) return;
    const shell = document.createElement("div");
    shell.className = "app-shell";
    shell.innerHTML = `
        <div class="sidebar-backdrop" data-sidebar-close></div>
        <aside class="sidebar" aria-label="Main navigation">
        <a class="brand" href="${navigation[role][0][2]}" aria-label="Supportly home">
            <span class="brand-mark" aria-hidden="true"><span></span><span></span></span>
            <span>Supportly</span>
        </a>
        <div class="sidebar-label">Workspace</div>
        <nav class="sidebar-nav">${navigation[role]
            .map((item) => navItem(item, currentPage))
            .join("")}</nav>
        <div class="sidebar-spacer"></div>
        <div class="sidebar-user">
            <div class="avatar">${initials(user.name)}</div>
            <div class="sidebar-user__details">
            <strong>${escapeHTML(user.name)}</strong>
            <span>${roleLabels[user.role]}</span>
            </div>
            <button class="icon-button icon-button--quiet" type="button" data-logout aria-label="Log out" title="Log out">${icons.logout}</button>
        </div>
        </aside>
        <div class="app-frame">
        <header class="topbar">
            <button class="icon-button mobile-menu" type="button" data-sidebar-open aria-label="Open navigation">${icons.menu}</button>
            <div class="topbar-title">
            <span>${escapeHTML(eyebrow || roleLabels[role])}</span>
            <h1>${escapeHTML(title)}</h1>
            </div>
            <div class="topbar-actions">
            <div class="topbar-profile">
                <div class="avatar avatar--small">${initials(user.name)}</div>
                <div><strong>${escapeHTML(user.name)}</strong><span>${roleLabels[user.role]}</span></div>
            </div>
            </div>
        </header>
        </div>`;
    document.body.prepend(shell);
    shell.querySelector(".app-frame").append(main);

    const openSidebar = () => document.body.classList.add("sidebar-open");
    const closeSidebar = () => document.body.classList.remove("sidebar-open");
    shell.querySelector("[data-sidebar-open]")?.addEventListener("click", openSidebar);
    shell.querySelector("[data-sidebar-close]")?.addEventListener("click", closeSidebar);
    shell.querySelector("[data-logout]")?.addEventListener("click", logout);
    shell.querySelectorAll(".nav-link").forEach((link) => {
        link.addEventListener("click", closeSidebar);
    });
}

export function statusBadge(status) {
    const slug = String(status).toLowerCase().replaceAll(" ", "-");
    return `<span class="badge status-${slug}"><span class="badge-dot"></span>${escapeHTML(status)}</span>`;
}

export function priorityBadge(priority) {
    return `<span class="badge priority-${String(priority).toLowerCase()}">${escapeHTML(priority)}</span>`;
}

export function accountBadge(status) {
    return `<span class="badge account-${String(status).toLowerCase()}"><span class="badge-dot"></span>${escapeHTML(status)}</span>`;
}

export function renderState(container, type, title, message = "") {
    if (!container) return;
    const symbols = { loading: "", empty: "○", error: "!" };
    container.innerHTML = `<div class="state state--${type}" role="${
        type === "error" ? "alert" : "status"
    }"><span class="state-symbol">${
        type === "loading" ? '<span class="spinner"></span>' : symbols[type]
    }</span><div><strong>${escapeHTML(title)}</strong>${
        message ? `<p>${escapeHTML(message)}</p>` : ""
    }</div></div>`;
}

export function showToast(message, type = "success") {
    let region = document.querySelector(".toast-region");
    if (!region) {
        region = document.createElement("div");
        region.className = "toast-region";
        region.setAttribute("aria-live", "polite");
        document.body.append(region);
    }
    const toast = document.createElement("div");
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `<span class="toast-icon">${type === "success" ? "✓" : "!"}</span><span>${escapeHTML(message)}</span>`;
    region.append(toast);
    window.setTimeout(() => toast.remove(), 3500);
}

export function openConfirmDialog({
    title,
    message,
    confirmLabel = "Confirm",
    danger = false,
}) {
    return new Promise((resolve) => {
        const dialog = document.createElement("dialog");
        dialog.className = "modal";
        dialog.innerHTML = `<form method="dialog" class="modal-card">
        <div class="modal-icon ${danger ? "modal-icon--danger" : ""}">${danger ? "!" : "?"}</div>
        <h2>${escapeHTML(title)}</h2>
        <p>${escapeHTML(message)}</p>
        <div class="modal-actions">
            <button class="button button--secondary" value="cancel">Cancel</button>
            <button class="button ${danger ? "button--danger" : "button--primary"}" value="confirm">${escapeHTML(confirmLabel)}</button>
        </div>
        </form>`;
        document.body.append(dialog);
        dialog.addEventListener("close", () => {
        resolve(dialog.returnValue === "confirm");
        dialog.remove();
        });
        dialog.showModal();
    });
}

export function openDetailsDialog({ title, subtitle = "", content }) {
    const dialog = document.createElement("dialog");
    dialog.className = "modal modal--wide";
    dialog.innerHTML = `<div class="modal-card">
        <div class="modal-heading"><div><h2>${escapeHTML(title)}</h2>${
        subtitle ? `<p>${escapeHTML(subtitle)}</p>` : ""
        }</div><button class="icon-button" type="button" data-close aria-label="Close dialog">×</button></div>
        <div class="modal-content">${content}</div>
        <div class="modal-actions"><button class="button button--secondary" type="button" data-close>Close</button></div>
    </div>`;
    document.body.append(dialog);
    dialog.querySelectorAll("[data-close]").forEach((button) =>
        button.addEventListener("click", () => dialog.close()),
    );
    dialog.addEventListener("close", () => dialog.remove());
    dialog.showModal();
}

export function setButtonBusy(button, busy, label = "Working…") {
    if (!button) return;
    if (!button.dataset.label) button.dataset.label = button.textContent;
    button.disabled = busy;
    button.classList.toggle("is-loading", busy);
    button.textContent = busy ? label : button.dataset.label;
}

export {icons};
