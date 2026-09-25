import {
    getCurrentUser,
    initLoginPage,
    initRegisterPage,
    protectRoute,
    redirectToRoleHome,
} from "./auth.js";
import {createAppShell, renderState} from "./ui.js";

import {
    initCreateTicket,
    initCustomerDashboard,
    initCustomerTicketDetails,
    initCustomerTickets,
} from "./customer.js";

import initChatbot from "./chatbot.js";

import {
    initAgentDashboard,
    initAgentTicketDetails,
    initAssignedTickets,
} from "./agent.js";

import {
    initAdminAgents,
    initAdminDashboard,
    initAdminTickets,
    initAdminUsers,
    initStatistics,
} from "./admin.js";

const controllers = {
    "customer-dashboard": initCustomerDashboard,
    "customer-tickets": initCustomerTickets,
    "customer-create-ticket": initCreateTicket,
    "customer-ticket-details": initCustomerTicketDetails,
    "customer-chatbot": initChatbot,
    "agent-dashboard": initAgentDashboard,
    "agent-assigned-tickets": initAssignedTickets,
    "agent-ticket-details": initAgentTicketDetails,
    "admin-dashboard": initAdminDashboard,
    "admin-users": initAdminUsers,
    "admin-agents": initAdminAgents,
    "admin-tickets": initAdminTickets,
    "admin-statistics": initStatistics,
};

async function initialize() {
    const { page, role, nav, title, eyebrow } = document.body.dataset;
    if (page === "index") {
        const user = getCurrentUser();
        if (user) redirectToRoleHome(user);
        else window.location.replace("/login.html");
        return;
    }
    if (page === "login") {
        initLoginPage();
        return;
    }
    if (page === "register") {
        initRegisterPage();
        return;
    }

    const user = await protectRoute(role);
    if (!user) return;
    createAppShell({
        user,
        role,
        currentPage: nav,
        title: title || document.title,
        eyebrow,
    });

    const controller = controllers[page];
    if (controller) {
        Promise.resolve(controller(user)).catch((error) => {
        console.error("Page initialization failed:", error);
        });
    }
}

const run = () => initialize().catch(error => {
    renderState(document.querySelector("#page-content"), "error", "Unable to load your session", error.message);
});
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run, { once: true });
} else run(); 
