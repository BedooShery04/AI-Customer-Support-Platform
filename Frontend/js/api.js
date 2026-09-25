import {CONFIG, ROLES, TICKET_CATEGORIES, TICKET_STATUSES} from "./config.js";

// This module is the only translation boundary between snake_case API contracts
// and the original frontend's camelCase view models. Mock files are never loaded
// during normal integrated operation.
const ticketCache = new Map();
const execute = async (mockCall, realCall) => CONFIG.USE_MOCK_API
    ? mockCall((await import("./mock-data.js")).MockAPI)
    : realCall();

export function normalizeUser(user) {
    return {
        ...user,
        createdAt: user.created_at ?? user.createdAt,
        status: user.status,
    };
}

export function normalizeTicket(ticket) {
    const value = {
        ...ticket,
        customerId: ticket.customer_id ?? ticket.customerId,
        customer: ticket.customer ?? null,
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
    const result = await apiRequest("/auth/login", {
        method: "POST",
        body: credentials
    });

    localStorage.setItem(CONFIG.TOKEN_STORAGE_KEY, result.access_token);

    const user = await getMe();

    return {
        ...result,
        user: normalizeUser(user)
    };
});

export const register = (payload) => execute(m => m.register(payload),
    () => apiRequest("/auth/register", { method: "POST", body: payload }));

export const getMe = () => execute(() => JSON.parse(localStorage.getItem(CONFIG.USER_STORAGE_KEY)),
    async () => normalizeUser(await apiRequest("/auth/me")));

export const logoutSession = () => Promise.resolve(null);

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

export const createTicket = payload =>
  execute(
    m => m.createTicket(payload),
    async () => {
      const created = await apiRequest("/tickets", {
        method: "POST",
        body: payload,
      });

      return normalizeTicket(created);
    }
  );

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

export const getAgents = () => execute(
    m => m.getUsers(ROLES.AGENT),
    async () => {
        const users = await getUsers(ROLES.AGENT);
        return users;
    }
);

export const updateUser = (id, changes) => execute(
    m => m.updateUser(id, changes),
    () => apiRequest(`/users/${encodeURIComponent(id)}`, {
        method: "PUT",
        body: changes,
    }).then(normalizeUser)
);

export const deleteUser = id => execute(m => m.deleteUser(id),
    () => apiRequest(`/users/${encodeURIComponent(id)}`, { method: "DELETE" }));

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
        const countBy = (key) =>
        tickets.reduce((counts, ticket) => {
            const value = ticket[key] || "Unassigned";
            counts[value] = (counts[value] || 0) + 1;
            return counts;
        }, {});

        const ticketsByCategory = countBy("category");
        const ticketsByStatus = countBy("status");
        const ticketsByAgent = countBy("assignedAgentId");

        const categoryCount = Object.keys(ticketsByCategory).length;

        return {
            total: tickets.length,
            open: tickets.filter(t => t.status === "Open").length,
            inProgress: tickets.filter(t => t.status === "In Progress").length,
            resolved: tickets.filter(t => t.status === "Resolved").length,
            critical: tickets.filter(t => t.priority === "Critical").length,

            recentTickets: tickets.slice(0, 5),

            tickets_by_category: ticketsByCategory,
            tickets_by_status: ticketsByStatus,
            tickets_by_agent: ticketsByAgent,

            average_tickets_per_category:
                categoryCount ? tickets.length / categoryCount : 0,
        };
    }
);