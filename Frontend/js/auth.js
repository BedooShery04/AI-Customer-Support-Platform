import {CONFIG, ROLE_HOME} from "./config.js";
import {login, register, getMe, logoutSession} from "./api.js";

export function getCurrentUser() {
    try {
        return JSON.parse(localStorage.getItem(CONFIG.USER_STORAGE_KEY));
    } catch {
        return null;
    }
}

export function setSession(session) {
    const token = session.access_token || session.token;
    if (!token) throw new Error("The server did not return an access token.");
    localStorage.setItem(CONFIG.TOKEN_STORAGE_KEY, token);
    localStorage.setItem(CONFIG.USER_STORAGE_KEY, JSON.stringify(session.user));
}

export function clearSession() {
    localStorage.removeItem(CONFIG.TOKEN_STORAGE_KEY);
    localStorage.removeItem(CONFIG.USER_STORAGE_KEY);
}

export function redirectToRoleHome(user = getCurrentUser()) {
    const destination = user && ROLE_HOME[user.role];
    window.location.replace(destination || "/login.html");
}

export async function protectRoute(expectedRole) {
    const user = getCurrentUser();
    const token = localStorage.getItem(CONFIG.TOKEN_STORAGE_KEY);
    if (!user || !token) {
        const returnTo = `${window.location.pathname}${window.location.search}`;
        window.location.replace(`/login.html?returnTo=${encodeURIComponent(returnTo)}`);
        return null;
    }
    const verifiedUser = await getMe();
    localStorage.setItem(CONFIG.USER_STORAGE_KEY, JSON.stringify(verifiedUser));
    if (expectedRole && verifiedUser.role !== expectedRole) {
        redirectToRoleHome(verifiedUser);
        return null;
    }
    return verifiedUser;
}

export async function logout() {
    try { await logoutSession(); }
    catch { /* Always clear local state, including when the server is offline. */ }
    finally {
        clearSession();
        window.location.replace("/login.html");
    }
}

function setFieldError(form, fieldName, message = "") {
    const field = form.elements[fieldName];
    const error = form.querySelector(`[data-error-for="${fieldName}"]`);
    if (field) field.setAttribute("aria-invalid", String(Boolean(message)));
    if (error) error.textContent = message;
}

function clearErrors(form) {
    form.querySelectorAll("[data-error-for]").forEach((element) => {
        element.textContent = "";
    });
    form.querySelectorAll("[aria-invalid]").forEach((element) => {
        element.setAttribute("aria-invalid", "false");
    });
}

function setFormMessage(form, type, message = "") {
    const alert = form.querySelector("[data-form-message]");
    if (!alert) return;
    alert.className = message ? `form-alert form-alert--${type}` : "form-alert hidden";
    alert.textContent = message;
}

function setBusy(button, busy, busyLabel) {
    if (!button) return;
    if (!button.dataset.defaultLabel) button.dataset.defaultLabel = button.textContent;
    button.disabled = busy;
    button.classList.toggle("is-loading", busy);
    button.textContent = busy ? busyLabel : button.dataset.defaultLabel;
}

function validateEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export function initLoginPage() {
    const existingUser = getCurrentUser();
    if (existingUser && localStorage.getItem(CONFIG.TOKEN_STORAGE_KEY)) {
        redirectToRoleHome(existingUser);
        return;
    }

    const form = document.querySelector("#login-form");
    const emailField = form?.elements.email;
    const pendingEmail = sessionStorage.getItem("registered_email");
    if (emailField && pendingEmail) {
        emailField.value = pendingEmail;
        sessionStorage.removeItem("registered_email");
        setFormMessage(form, "success", "Registration complete. Sign in to continue.");
    }

    document.querySelectorAll("[data-demo-email]").forEach((button) => {
        button.addEventListener("click", () => {
        emailField.value = button.dataset.demoEmail;
        if (button.dataset.demoPassword) form.elements.password.value = button.dataset.demoPassword;
        form.elements.password.focus();
        });
    });

    form?.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearErrors(form);
        setFormMessage(form, "error", "");
        const email = form.elements.email.value.trim();
        const password = form.elements.password.value;
        let valid = true;
        if (!validateEmail(email)) {
        setFieldError(form, "email", "Enter a valid email address.");
        valid = false;
        }
        if (password.length < 8) {
        setFieldError(form, "password", "Password must contain at least 8 characters.");
        valid = false;
        }
        if (!valid) return;

        const button = form.querySelector("button[type='submit']");
        setBusy(button, true, "Signing in…");
        try {
        const session = await login({ email, password });
        setSession(session);
        const returnTo = new URLSearchParams(window.location.search).get("returnTo");
        let safeReturn = null;
        try {
            const url = new URL(returnTo || "", window.location.origin);
            const rolePrefix = `/${session.user.role.toLowerCase()}/`;
            if (url.origin === window.location.origin && url.pathname.startsWith(rolePrefix)) {
            safeReturn = url.pathname + url.search;
            }
        } catch { /* Ignore malformed or external redirect targets. */ }
        window.location.replace(safeReturn || ROLE_HOME[session.user.role]);
        } catch (error) {
        setFormMessage(form, "error", error.message || "Unable to sign in.");
        } finally {
        setBusy(button, false, "Signing in…");
        }
    });
}

export function initRegisterPage() {
    const form = document.querySelector("#register-form");
    form?.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearErrors(form);
        setFormMessage(form, "error", "");

        const payload = {
        name: form.elements.name.value.trim(),
        email: form.elements.email.value.trim(),
        password: form.elements.password.value,
        };
        const confirmation = form.elements.confirmPassword.value;
        let valid = true;
        if (payload.name.length < 2) {
        setFieldError(form, "name", "Enter your full name.");
        valid = false;
        }
        if (!validateEmail(payload.email)) {
        setFieldError(form, "email", "Enter a valid email address.");
        valid = false;
        }
        if (payload.password.length < 8) {
        setFieldError(form, "password", "Use at least 8 characters.");
        valid = false;
        }
        if (confirmation !== payload.password) {
        setFieldError(form, "confirmPassword", "Passwords do not match.");
        valid = false;
        }
        if (!valid) return;

        const button = form.querySelector("button[type='submit']");
        setBusy(button, true, "Creating account…");
        try {
        await register(payload);
        setFormMessage(form, "success", "Account created successfully. Redirecting…");
        sessionStorage.setItem("registered_email", payload.email);
        window.setTimeout(() => window.location.replace("/login.html"), 650);
        } catch (error) {
        setFormMessage(form, "error", error.message || "Unable to create your account.");
        } finally {
        setBusy(button, false, "Creating account…");
        }
    });
}