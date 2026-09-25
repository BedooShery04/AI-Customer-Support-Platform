import {CONFIG, ROLES, TICKET_CATEGORIES, TICKET_STATUSES} from "./config.js";

// This module is the only translation boundary between snake_case API contracts
// and the original frontend's camelCase view models. Mock files are never loaded
// during normal integrated operation.
const ticketCache = new Map();
const execute = async (mockCall, realCall) => CONFIG.USE_MOCK_API
    ? mockCall((await import("./mock-data.js")).MockAPI)
    : realCall();

    // export function normalizeUser(user) {
//     return {
//         ...user,
//         createdAt: user.created_date ?? user.createdAt,
//         status: user.account_status === "ACTIVE" ? "Active"
//         : user.account_status === "DISABLED" ? "Disabled" : user.status };
// }

// ENUM

// {
//   "id": 2,
//   "name": "Ahmed",
//   "email": "ahmed@example.com",
//   "role": "customer",
//   "created_at": "...",
//   "status": "active"
// }

export function normalizeUser(user) {
    return {
        ...user,
        createdAt: user.created_at ?? user.createdAt,
        status: user.status,
    };
}

// export function normalizeTicket(ticket) {
//     const value = { ...ticket, customerId: ticket.customer_id ?? ticket.customerId,
//         assignedAgentId: ticket.assigned_agent_id ?? ticket.assignedAgentId ?? null,
//         assignedAgent: ticket.assigned_agent ?? ticket.assignedAgent ?? null,
//         createdAt: ticket.created_date ?? ticket.createdAt, updatedAt: ticket.updated_date ?? ticket.updatedAt,
//         aiClassification: ticket.ai_summary ? { summary: ticket.ai_summary,
//         suggestedAction: ticket.ai_suggested_action, category: ticket.ai_category, priority: ticket.ai_priority }
//         : ticket.aiClassification ?? null };
//     ticketCache.set(value.id, value);
//     return value;
// }

// {
//   "customer_id": 1,
//   "assigned_agent_id": 2,
//   "created_at": "...",
//   "updated_at": "..."
// }

export function normalizeTicket(ticket) {
    const value = {
        ...ticket,
        customerId: ticket.customer_id ?? ticket.customerId,
        assignedAgentId: ticket.assigned_agent_id ?? ticket.assignedAgentId ?? null,
        createdAt: ticket.created_at ?? ticket.createdAt,
        updatedAt: ticket.updated_at ?? ticket.updatedAt,

        aiClassification: ticket.ai_summary
        ? {
            summary: ticket.ai_summary,
            suggestedAction: ticket.ai_suggested_action,
            category: ticket.ai_category,
            priority: ticket.ai_priority,
            }
        : ticket.aiClassification ?? null,
    };

    ticketCache.set(value.id, value);
    return value;
}

// const normalizeMessage = (item) => ({
//     ...item,
//     senderRole: item.sender_role ?? item.senderRole,
//     senderName: item.sender_name ?? item.senderName,
//     senderId: item.sender_id ?? item.senderId,
//     timestamp: item.created_at ?? item.timestamp,
// });

const normalizeMessage = (item) => ({
    ...item,
    role: item.role === "assistant" ? "ai" : item.role,
    senderRole: item.sender_role ?? item.senderRole,
    senderName: item.sender_name ?? item.senderName,
    senderId: item.sender_id ?? item.senderId,
    timestamp: item.created_at ?? item.timestamp,
});

function errorText(payload) {
    if (typeof payload?.detail === "string") return payload.detail;
    if (Array.isArray(payload?.detail)) return payload.detail.map(x => x.msg || "Invalid value").join("; ");
    return payload?.message || "The request failed.";
}
export async function apiRequest(path, options = {}) {
    const headers = new Headers(options.headers || {});
    const token = localStorage.getItem(CONFIG.TOKEN_STORAGE_KEY);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const isJSON = options.body !== undefined && !(options.body instanceof FormData);
    if (isJSON) headers.set("Content-Type", "application/json");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 120000);
    let response;
    try {
        response = await fetch(`${CONFIG.API_BASE_URL}${path}`, { ...options, headers,
        signal: options.signal || controller.signal,
        body: isJSON ? JSON.stringify(options.body) : options.body });
    } catch (error) {
        throw new Error(error.name === "AbortError"
        ? "The request timed out. Check your tickets before retrying; the action may have completed."
        : "Cannot reach FastAPI. Start START_WINDOWS.bat, then open the website at http://127.0.0.1:8000.");
    } finally { window.clearTimeout(timeout); }
    if (response.status === 204) return null;
    const isJsonResponse = (response.headers.get("content-type") || "").includes("application/json");
    const payload = isJsonResponse ? await response.json() : null;
    if (!response.ok) {
        const error = new Error(errorText(payload));
        error.status = response.status;
        error.code = payload?.code;
        if (response.status === 401 && !["/auth/login", "/auth/register"].includes(path)) {
        localStorage.removeItem(CONFIG.TOKEN_STORAGE_KEY);
        localStorage.removeItem(CONFIG.USER_STORAGE_KEY);
        window.location.replace("/login.html?expired=1");
        }
        throw error;
    }
    return payload;
}

export const login = (credentials) => execute(m => m.login(credentials), async () => {
    const result = await apiRequest("/auth/login", { method: "POST", body: credentials });
    return { ...result, user: normalizeUser(result.user) };
});

export const register = (payload) => execute(m => m.register(payload),
    () => apiRequest("/auth/register", { method: "POST", body: payload }));

export const getMe = () => execute(() => JSON.parse(localStorage.getItem(CONFIG.USER_STORAGE_KEY)),
    async () => normalizeUser(await apiRequest("/auth/me")));

// export const logoutSession = () => execute(() => null,
//     () => apiRequest("/auth/logout", { method: "POST" }));

export const logoutSession = () => Promise.resolve(null);

// export const getTickets = (filters = {}) => execute(m => m.getTickets(filters), async () => {
//   const query = new URLSearchParams(Object.entries(filters)
//     .map(([key, value]) => [key === "assignedAgentId" ? "assigned_agent_id" : key, value])
//     .filter(([, value]) => value !== "" && value !== null && value !== undefined)).toString();
//   return (await apiRequest(`/tickets${query ? `?${query}` : ""}`)).map(normalizeTicket);
// });

export const getTickets = (filters = {}) => execute(
    m => m.getTickets(filters),
    async () => {
        const currentUser = JSON.parse(
        localStorage.getItem(CONFIG.USER_STORAGE_KEY) || "null"
        );

        let path = "/tickets";

        if (currentUser?.role === ROLES.CUSTOMER) {
        path = "/tickets/my";
        } else if (currentUser?.role === ROLES.AGENT) {
        path = "/tickets/assigned";
        }

        return (await apiRequest(path)).map(normalizeTicket);
    }
);

export const getTicketById = id => execute(m => m.getTicketById(id),
    async () => normalizeTicket(await apiRequest(`/tickets/${encodeURIComponent(id)}`)));

export const classifyTicket = id => apiRequest("/ai/classify-ticket", { method: "POST", body: { ticket_id: id } });

export const createTicket = payload => execute(m => m.createTicket(payload), async () => {
    const created = await apiRequest("/tickets", { method: "POST", body: payload });
    const ticket = normalizeTicket(created);
    try {
        const classification = await classifyTicket(created.id);
        ticket.aiClassification = { summary: classification.short_summary, suggestedAction: classification.suggested_action };
    } catch (error) {
        // Ticket creation succeeded. A failed optional classification must not look like a failed create.
        ticket.classificationWarning = "Ticket saved. AI classification is currently unavailable.";
    }
    return ticket;
});

export function changedTicketFields(original, values) {
    return Object.fromEntries(Object.entries(values).filter(([key, value]) => value !== original[key]));
}

export const updateTicket = (id, changes) => execute(m => m.updateTicket(id, changes), async () => {
    if (!Object.keys(changes).length) {
        return ticketCache.get(id) || getTicketById(id); // Documented no-change form submission.
    }
    const body = Object.fromEntries(Object.entries(changes)
        .map(([key, value]) => [key === "assignedAgentId" ? "assigned_agent_id" : key, value]));
    return normalizeTicket(await apiRequest(`/tickets/${encodeURIComponent(id)}`, { method: "PUT", body }));
});

export const deleteTicket = id => execute(m => m.deleteTicket(id),
    () => apiRequest(`/tickets/${encodeURIComponent(id)}`, { method: "DELETE" }));

export const getTicketMessages = id => execute(m => m.getTicketMessages(id),
    async () => (await apiRequest(`/tickets/${encodeURIComponent(id)}/messages`)).map(normalizeMessage));

export const sendTicketMessage = (id, message) => execute(m => m.sendTicketMessage(id, message),
    async () => normalizeMessage(await apiRequest(`/tickets/${encodeURIComponent(id)}/messages`, { method: "POST", body: { message } })));
  
// export const sendChatMessage = message => execute(m => m.sendChatMessage(message),
//     () => apiRequest("/ai/chat", { method: "POST", body: { message } }));

export const sendChatMessage = message => execute(
    m => m.sendChatMessage(message),
    async () => {
        const response = await apiRequest("/ai/chat", {
            method: "POST",
            body: { message },
        });

        return {
            role: "ai",
            message: response.message,
            timestamp: new Date().toISOString(),
        };
    }
);

export const getChatMessages = () => execute(m => m.getChatMessages(), () => apiRequest("/ai/chat/messages"));

export const generateAIResponseSuggestion = id => execute(m => m.generateAIResponseSuggestion(id),
    () => apiRequest("/ai/suggest-response", { method: "POST", body: { ticket_id: id } }));

// export const getUsers = (role = ROLES.CUSTOMER) => execute(m => m.getUsers(role),
//     async () => (await apiRequest(`/users?role=${encodeURIComponent(role)}`)).map(normalizeUser));

// عشان ما نبوظش الـ frontend، عندنا حل بسيط: نخلي /users يرجع كل المستخدمين، وبعدها نعمل filtering في api.js.

export const getUsers = (role = null) => execute(
    m => m.getUsers(role),
    async () => {
        const users = (await apiRequest("/users")).map(normalizeUser);

        if (!role) {
        return users;
        }

        return users.filter(user => user.role === role);
    }
);

export const getUser = id => apiRequest(`/users/${encodeURIComponent(id)}`).then(normalizeUser);

// export const getAgents = () => execute(m => m.getUsers(ROLES.AGENT), async () => {
//     const current = JSON.parse(localStorage.getItem(CONFIG.USER_STORAGE_KEY) || "null");
//     const path = current?.role === ROLES.AGENT ? "/tickets/assignees" : "/users?role=AGENT";
//     return (await apiRequest(path)).map(normalizeUser);
// });

// لكن فيه نقطة permissions:

export const getAgents = () => execute(
    m => m.getUsers(ROLES.AGENT),
    async () => {
        const users = await getUsers(ROLES.AGENT);
        return users;
    }
);

// export const updateUser = (id, changes) => execute(m => m.updateUser(id, changes),
//     () => apiRequest(`/users/${encodeURIComponent(id)}`, { method: "PUT",
//         body: { account_status: (changes.account_status || changes.status).toUpperCase() } }));

export const updateUser = (id, changes) => execute(
    m => m.updateUser(id, changes),
    () => apiRequest(`/users/${encodeURIComponent(id)}`, {
        method: "PUT",
        body: changes,
    }).then(normalizeUser)
);

export const deleteUser = id => execute(m => m.deleteUser(id),
    () => apiRequest(`/users/${encodeURIComponent(id)}`, { method: "DELETE" }));

// export const getDashboardStats = () => execute(async m => {
//     const tickets = await m.getTickets();
//     const users = JSON.parse(localStorage.getItem(CONFIG.USER_STORAGE_KEY) || "null");
//     const agents = users?.role === ROLES.ADMIN ? await m.getUsers(ROLES.AGENT) : [];
//     return { total: tickets.length, open: tickets.filter(t => t.status === "Open").length,
//         inProgress: tickets.filter(t => t.status === "In Progress").length,
//         resolved: tickets.filter(t => t.status === "Resolved").length,
//         critical: tickets.filter(t => t.priority === "Critical").length, recentTickets: tickets.slice(0,5),
//         average_tickets_per_category: tickets.length / TICKET_CATEGORIES.length,
//         tickets_by_category: Object.fromEntries(TICKET_CATEGORIES.map(c => [c,tickets.filter(t => t.category === c).length])),
//         tickets_by_status: Object.fromEntries(TICKET_STATUSES.map(s => [s,tickets.filter(t => t.status === s).length])),
//         support_activity: agents.map(a => ({ agent_id:a.id,agent_name:a.name,assigned_tickets:tickets.filter(t => t.assignedAgentId === a.id).length })),
//         tickets_by_agent:{ Unassigned:tickets.filter(t => !t.assignedAgentId).length }, ai_activity:{} };
// }, async () => {
//     const data = await apiRequest("/dashboard/stats");
//     return { ...data, total: data.assigned_tickets ?? data.total_tickets,
//         open: data.open_tickets, inProgress: data.in_progress_tickets, resolved: data.resolved_tickets,
//         critical: data.critical_tickets ?? 0, recentTickets: (data.recent_tickets || []).map(normalizeTicket) };
// });


export const getDashboardStats = () => execute(
    async m => {
        const tickets = await m.getTickets();
        return {
        total: tickets.length,
        open: tickets.filter(t => t.status === "Open").length,
        inProgress: tickets.filter(t => t.status === "In Progress").length,
        resolved: tickets.filter(t => t.status === "Resolved").length,
        recentTickets: tickets.slice(0, 5),
        };
    },
    async () => {
        const currentUser = JSON.parse(
        localStorage.getItem(CONFIG.USER_STORAGE_KEY) || "null"
        );

        let path = "/tickets";

        if (currentUser?.role === ROLES.CUSTOMER) {
        path = "/tickets/my";
        } else if (currentUser?.role === ROLES.AGENT) {
        path = "/tickets/assigned";
        }

        const tickets = (await apiRequest(path)).map(normalizeTicket);

        return {
        total: tickets.length,
        open: tickets.filter(t => t.status === "Open").length,
        inProgress: tickets.filter(t => t.status === "In Progress").length,
        resolved: tickets.filter(t => t.status === "Resolved").length,
        recentTickets: tickets.slice(0, 5),
        };
    }
);