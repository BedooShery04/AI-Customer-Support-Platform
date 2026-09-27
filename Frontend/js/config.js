export const CONFIG = Object.freeze({
	API_BASE_URL:
		window.location.port === "5500"
			? `${window.location.protocol}//${window.location.hostname}:8000`
			: window.location.origin,

	TOKEN_STORAGE_KEY:
		"support_platform_token",

	USER_STORAGE_KEY:
		"support_platform_user"
});

export const ROLES = Object.freeze({
	CUSTOMER: "customer",
	AGENT: "agent",
	ADMIN: "admin",
});

export const TICKET_STATUSES = Object.freeze([
	"Open",
	"In Progress",
	"Waiting for Customer",
	"Resolved",
	"Closed",
]);

export const TICKET_PRIORITIES = Object.freeze([
	"Low",
	"Medium",
	"High",
	"Critical",
]);

export const TICKET_CATEGORIES = Object.freeze([
	"Technical Issue",
	"Account Issue",
	"Billing",
	"Product Issue",
	"General Inquiry",
]);

export const ROLE_HOME = Object.freeze({
	customer: "/customer/dashboard.html",
	agent: "/agent/dashboard.html",
	admin: "/admin/dashboard.html",
});
