import {
  CONFIG,
  ROLES,
  TICKET_CATEGORIES,
  TICKET_PRIORITIES,
  TICKET_STATUSES,
} from "./config.js";

const seedData = {
  users: [
    {
      id: "USR-001",
      name: "Olivia Martin",
      email: "customer@demo.com",
      role: ROLES.CUSTOMER,
      createdAt: "2026-08-12T09:20:00Z",
      status: "Active",
    },
    {
      id: "USR-002",
      name: "Daniel Wilson",
      email: "daniel@demo.com",
      role: ROLES.CUSTOMER,
      createdAt: "2026-08-18T13:45:00Z",
      status: "Active",
    },
    {
      id: "AGT-001",
      name: "Maya Rodriguez",
      email: "agent@demo.com",
      role: ROLES.AGENT,
      createdAt: "2026-07-04T08:00:00Z",
      status: "Active",
    },
    {
      id: "AGT-002",
      name: "Noah Kim",
      email: "noah.agent@demo.com",
      role: ROLES.AGENT,
      createdAt: "2026-07-12T08:00:00Z",
      status: "Active",
    },
    {
      id: "ADM-001",
      name: "Elena Brooks",
      email: "admin@demo.com",
      role: ROLES.ADMIN,
      createdAt: "2026-06-01T08:00:00Z",
      status: "Active",
    },
  ],
  tickets: [
    {
      id: "TKT-1048",
      customerId: "USR-001",
      subject: "Cannot connect my workspace",
      description:
        "The desktop application keeps showing a connection error after I sign in. I restarted it twice but the issue continues.",
      category: "Technical Issue",
      priority: "High",
      status: "In Progress",
      assignedAgentId: "AGT-001",
      createdAt: "2026-09-21T08:35:00Z",
      updatedAt: "2026-09-23T10:10:00Z",
      aiClassification: {
        summary:
          "Customer cannot connect the desktop application after successful sign-in.",
        suggestedAction:
          "Confirm the application version, review network restrictions, and collect the connection error code.",
      },
    },
    {
      id: "TKT-1046",
      customerId: "USR-001",
      subject: "Question about my latest invoice",
      description:
        "I need clarification about the service charge shown on my September invoice.",
      category: "Billing",
      priority: "Low",
      status: "Resolved",
      assignedAgentId: "AGT-002",
      createdAt: "2026-09-18T11:15:00Z",
      updatedAt: "2026-09-19T15:30:00Z",
    },
    {
      id: "TKT-1042",
      customerId: "USR-001",
      subject: "Update the email on my account",
      description:
        "I no longer use my old company email and need help updating the account email.",
      category: "Account Issue",
      priority: "Medium",
      status: "Waiting for Customer",
      assignedAgentId: "AGT-001",
      createdAt: "2026-09-15T07:50:00Z",
      updatedAt: "2026-09-20T12:00:00Z",
    },
    {
      id: "TKT-1039",
      customerId: "USR-002",
      subject: "Production reports are unavailable",
      description:
        "Our team cannot open any production report. The page returns an error for every user.",
      category: "Product Issue",
      priority: "Critical",
      status: "Open",
      assignedAgentId: "AGT-002",
      createdAt: "2026-09-14T16:25:00Z",
      updatedAt: "2026-09-23T09:42:00Z",
    },
    {
      id: "TKT-1035",
      customerId: "USR-002",
      subject: "How can I export a report?",
      description:
        "Please explain where I can export the monthly report from the dashboard.",
      category: "General Inquiry",
      priority: "Low",
      status: "Closed",
      assignedAgentId: "AGT-001",
      createdAt: "2026-09-10T10:00:00Z",
      updatedAt: "2026-09-11T14:20:00Z",
    },
  ],
  messages: {
    "TKT-1048": [
      {
        id: "MSG-001",
        senderId: "USR-001",
        senderRole: ROLES.CUSTOMER,
        senderName: "Olivia Martin",
        message:
          "The connection error started this morning. Other websites work normally.",
        timestamp: "2026-09-21T08:35:00Z",
      },
      {
        id: "MSG-002",
        senderId: "AGT-001",
        senderRole: ROLES.AGENT,
        senderName: "Maya Rodriguez",
        message:
          "Thanks for the details. Please confirm the application version shown under Help > About.",
        timestamp: "2026-09-21T09:12:00Z",
      },
      {
        id: "MSG-003",
        senderId: "USR-001",
        senderRole: ROLES.CUSTOMER,
        senderName: "Olivia Martin",
        message: "It is version 5.8.2 on Windows 11.",
        timestamp: "2026-09-23T10:10:00Z",
      },
    ],
    "TKT-1046": [
      {
        id: "MSG-004",
        senderId: "USR-001",
        senderRole: ROLES.CUSTOMER,
        senderName: "Olivia Martin",
        message: "Could you explain the additional service charge?",
        timestamp: "2026-09-18T11:15:00Z",
      },
      {
        id: "MSG-005",
        senderId: "AGT-002",
        senderRole: ROLES.AGENT,
        senderName: "Noah Kim",
        message:
          "The charge covers the additional workspace activated on September 5. I have emailed the invoice breakdown.",
        timestamp: "2026-09-19T15:30:00Z",
      },
    ],
    "TKT-1042": [
      {
        id: "MSG-006",
        senderId: "AGT-001",
        senderRole: ROLES.AGENT,
        senderName: "Maya Rodriguez",
        message:
          "Please reply with the new email address you would like us to review.",
        timestamp: "2026-09-20T12:00:00Z",
      },
    ],
    "TKT-1039": [],
    "TKT-1035": [],
  },
  chatbotMessages: [
    {
      id: "CHAT-001",
      role: "ai",
      message:
        "Hello Olivia. I can answer support questions and help you check your tickets. How can I help?",
      timestamp: "2026-09-23T08:00:00Z",
    },
  ],
};

const clone = (value) => JSON.parse(JSON.stringify(value));
const delay = (ms = CONFIG.MOCK_DELAY_MS) =>
  new Promise((resolve) => window.setTimeout(resolve, ms));

function getDatabase() {
  const current = localStorage.getItem(CONFIG.MOCK_DB_STORAGE_KEY);
  if (current) {
    try {
      return JSON.parse(current);
    } catch {
      localStorage.removeItem(CONFIG.MOCK_DB_STORAGE_KEY);
    }
  }
  const fresh = clone(seedData);
  localStorage.setItem(CONFIG.MOCK_DB_STORAGE_KEY, JSON.stringify(fresh));
  return fresh;
}

function saveDatabase(database) {
  localStorage.setItem(CONFIG.MOCK_DB_STORAGE_KEY, JSON.stringify(database));
}

function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem(CONFIG.USER_STORAGE_KEY));
  } catch {
    return null;
  }
}

function createId(prefix) {
  return `${prefix}-${Date.now().toString().slice(-6)}`;
}

function ensureAllowed(value, allowed, label) {
  if (!allowed.includes(value)) {
    throw new Error(`Invalid ${label}.`);
  }
}

export const MockAPI = {
  async login(credentials) {
    await delay();
    const database = getDatabase();
    const user = database.users.find(
      (item) => item.email.toLowerCase() === credentials.email.toLowerCase(),
    );
    if (!user || credentials.password.length < 8) {
      throw new Error("The email or password is incorrect.");
    }
    if (user.status !== "Active") {
      throw new Error("This account is disabled. Contact an administrator.");
    }
    return {
      token: `mock-jwt-${user.id}-${Date.now()}`,
      user: clone(user),
    };
  },

  async register(payload) {
    await delay();
    const database = getDatabase();
    const exists = database.users.some(
      (user) => user.email.toLowerCase() === payload.email.toLowerCase(),
    );
    if (exists) throw new Error("An account with this email already exists.");
    const user = {
      id: createId("USR"),
      name: payload.name.trim(),
      email: payload.email.trim().toLowerCase(),
      role: ROLES.CUSTOMER,
      createdAt: new Date().toISOString(),
      status: "Active",
    };
    database.users.push(user);
    saveDatabase(database);
    return clone(user);
  },

  async getTickets(filters = {}) {
    await delay();
    const database = getDatabase();
    const user = getCurrentUser();
    let tickets = [...database.tickets];
    if (user?.role === ROLES.CUSTOMER) {
      tickets = tickets.filter((ticket) => ticket.customerId === user.id);
    }
    if (user?.role === ROLES.AGENT) {
      tickets = tickets.filter((ticket) => ticket.assignedAgentId === user.id);
    }
    Object.entries(filters).forEach(([key, value]) => {
      if (value) tickets = tickets.filter((ticket) => ticket[key] === value);
    });
    return clone(
      tickets
        .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
        .map((ticket) => ({
          ...ticket,
          customer: database.users.find((userItem) => userItem.id === ticket.customerId),
          assignedAgent: database.users.find(
            (userItem) => userItem.id === ticket.assignedAgentId,
          ),
        })),
    );
  },

  async getTicketById(ticketId) {
    await delay();
    const database = getDatabase();
    const user = getCurrentUser();
    const ticket = database.tickets.find((item) => item.id === ticketId);
    if (!ticket) throw new Error("Ticket not found.");
    if (user?.role === ROLES.CUSTOMER && ticket.customerId !== user.id) {
      throw new Error("You do not have access to this ticket.");
    }
    if (user?.role === ROLES.AGENT && ticket.assignedAgentId !== user.id) {
      throw new Error("This ticket is not assigned to you.");
    }
    return clone({
      ...ticket,
      customer: database.users.find((item) => item.id === ticket.customerId),
      assignedAgent: database.users.find((item) => item.id === ticket.assignedAgentId),
    });
  },

  async createTicket(payload) {
    await delay();
    const database = getDatabase();
    const user = getCurrentUser();
    ensureAllowed(payload.category, TICKET_CATEGORIES, "category");
    ensureAllowed(payload.priority, TICKET_PRIORITIES, "priority");
    const now = new Date().toISOString();
    const ticket = {
      id: createId("TKT"),
      customerId: user.id,
      subject: payload.subject.trim(),
      description: payload.description.trim(),
      category: payload.category,
      priority: payload.priority,
      status: "Open",
      assignedAgentId: null,
      createdAt: now,
      updatedAt: now,
    };
    database.tickets.unshift(ticket);
    database.messages[ticket.id] = [];
    saveDatabase(database);
    return clone(ticket);
  },

  async updateTicket(ticketId, updates) {
    await delay();
    const database = getDatabase();
    const ticket = database.tickets.find((item) => item.id === ticketId);
    if (!ticket) throw new Error("Ticket not found.");
    if (updates.status) ensureAllowed(updates.status, TICKET_STATUSES, "status");
    if (updates.priority) ensureAllowed(updates.priority, TICKET_PRIORITIES, "priority");
    Object.assign(ticket, updates, { updatedAt: new Date().toISOString() });
    saveDatabase(database);
    return clone(ticket);
  },

  async deleteTicket(ticketId) {
    await delay();
    const database = getDatabase();
    database.tickets = database.tickets.filter((ticket) => ticket.id !== ticketId);
    delete database.messages[ticketId];
    saveDatabase(database);
    return { success: true };
  },

  async getTicketMessages(ticketId) {
    await delay();
    const database = getDatabase();
    return clone(database.messages[ticketId] || []);
  },

  async sendTicketMessage(ticketId, message) {
    await delay();
    const database = getDatabase();
    const user = getCurrentUser();
    const ticket = database.tickets.find((item) => item.id === ticketId);
    if (!ticket) throw new Error("Ticket not found.");
    const newMessage = {
      id: createId("MSG"),
      senderId: user.id,
      senderRole: user.role,
      senderName: user.name,
      message: message.trim(),
      timestamp: new Date().toISOString(),
    };
    database.messages[ticketId] ||= [];
    database.messages[ticketId].push(newMessage);
    ticket.updatedAt = newMessage.timestamp;
    saveDatabase(database);
    return clone(newMessage);
  },

  async getUsers(role) {
    await delay();
    const database = getDatabase();
    return clone(database.users.filter((user) => !role || user.role === role));
  },

  async updateUser(userId, updates) {
    await delay();
    const database = getDatabase();
    const user = database.users.find((item) => item.id === userId);
    if (!user) throw new Error("User not found.");
    Object.assign(user, updates);
    saveDatabase(database);
    return clone(user);
  },

  async deleteUser(userId) {
    await delay();
    const database = getDatabase();
    database.users = database.users.filter((user) => user.id !== userId);
    database.tickets.forEach((ticket) => {
      if (ticket.assignedAgentId === userId) ticket.assignedAgentId = null;
    });
    saveDatabase(database);
    return { success: true };
  },

  async sendChatMessage(message) {
    await delay(650);
    const database = getDatabase();
    const userMessage = {
      id: createId("CHAT"),
      role: "user",
      message: message.trim(),
      timestamp: new Date().toISOString(),
    };
    const normalized = message.toLowerCase();
    let reply =
      "I can help with support questions. For account-specific actions, I will use the secure support service when the backend is connected.";
    if (normalized.includes("status") || normalized.includes("ticket")) {
      const user = getCurrentUser();
      const customerTickets = database.tickets.filter(
        (ticket) => ticket.customerId === user?.id,
      );
      reply = customerTickets.length
        ? `You currently have ${customerTickets.length} ticket${customerTickets.length === 1 ? "" : "s"}. Your most recently updated ticket is ${customerTickets[0].id}, with status “${customerTickets[0].status}”.`
        : "You do not have any tickets yet.";
    } else if (normalized.includes("hello") || normalized.includes("hi")) {
      reply = "Hello! How can I help with your support request today?";
    }
    const aiMessage = {
      id: createId("CHAT"),
      role: "ai",
      message: reply,
      timestamp: new Date().toISOString(),
    };
    database.chatbotMessages.push(userMessage, aiMessage);
    saveDatabase(database);
    return clone(aiMessage);
  },

  async getChatMessages() {
    await delay(150);
    return clone(getDatabase().chatbotMessages);
  },

  async generateAIResponseSuggestion(ticketId) {
    await delay(780);
    const database = getDatabase();
    const ticket = database.tickets.find((item) => item.id === ticketId);
    if (!ticket) throw new Error("Ticket not found.");
    return {
      suggestion: `Hello, thank you for the update regarding “${ticket.subject}”. I have reviewed the details and I’m checking the next appropriate step. Please allow us a little time to investigate, and we will keep you updated here.`,
    };
  },
};

export function resetMockDatabase() {
  localStorage.removeItem(CONFIG.MOCK_DB_STORAGE_KEY);
  return getDatabase();
}
