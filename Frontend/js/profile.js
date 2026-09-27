import { getMe, updateMyProfile } from "./api.js";
import { CONFIG } from "./config.js";

import {
    escapeHTML,
    formatDate,
    initials,
    setButtonBusy,
    showToast,
} from "./ui.js";

const roleLabels = {
    customer: "Customer",
    agent: "Support Agent",
    admin: "Administrator",
};

function getRoleLabel(role) {
    return roleLabels[String(role).toLowerCase()] || role;
}

function renderProfile(user) {
    document.querySelector("#profile-avatar").textContent =
        initials(user.name);

    document.querySelector("#profile-name").textContent =
        user.name;

    document.querySelector("#profile-email").textContent =
        user.email;

    document.querySelector("#profile-role").textContent =
        getRoleLabel(user.role);

    document.querySelector("#profile-info-role").textContent =
        getRoleLabel(user.role);

    document.querySelector("#profile-status").textContent =
        user.status || "—";

    document.querySelector("#profile-created").textContent =
        formatDate(user.createdAt ?? user.created_at);

    const form = document.querySelector("#profile-form");

    form.elements.name.value = user.name;
    form.elements.email.value = user.email;
}

function clearFormErrors(form) {
    form.querySelectorAll("[data-error-for]").forEach((element) => {
        element.textContent = "";
    });

    form.querySelectorAll("[aria-invalid]").forEach((element) => {
        element.setAttribute("aria-invalid", "false");
    });
}

function setFieldError(form, field, message) {
    form.elements[field].setAttribute("aria-invalid", "true");

    const error = form.querySelector(
        `[data-error-for="${field}"]`,
    );

    if (error) {
        error.textContent = message;
    }
}

function setFormMessage(message, type = "error") {
    const element = document.querySelector("#profile-message");

    element.textContent = message;
    element.className = message
        ? `form-alert form-alert--${type}`
        : "form-alert hidden";
}

function updateShell(user) {
    document.querySelectorAll(".sidebar-user .avatar").forEach(
        (element) => {
            element.textContent = initials(user.name);
        },
    );

    document.querySelectorAll(
        ".sidebar-user__details strong",
    ).forEach((element) => {
        element.textContent = user.name;
    });

    document.querySelectorAll(
        ".topbar-profile .avatar",
    ).forEach((element) => {
        element.textContent = initials(user.name);
    });

    document.querySelectorAll(
        ".topbar-profile strong",
    ).forEach((element) => {
        element.textContent = user.name;
    });
}

export async function initMyProfile(user) {
    const form = document.querySelector("#profile-form");

    if (!form) return;

    let savedUser = user;

    try {
        savedUser = await getMe();
    } catch (error) {
        console.error("Unable to refresh profile:", error);
    }

    renderProfile(savedUser);

    form.addEventListener("reset", (event) => {
        event.preventDefault();

        clearFormErrors(form);
        setFormMessage("");

        form.elements.name.value = savedUser.name;
        form.elements.email.value = savedUser.email;
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        clearFormErrors(form);
        setFormMessage("");

        const name = form.elements.name.value.trim();
        const email = form.elements.email.value.trim();

        let valid = true;

        if (name.length < 2) {
            setFieldError(
                form,
                "name",
                "Name must contain at least 2 characters.",
            );

            valid = false;
        }

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            setFieldError(
                form,
                "email",
                "Enter a valid email address.",
            );

            valid = false;
        }

        if (!valid) return;

        const changes = {};

        if (name !== savedUser.name) {
            changes.name = name;
        }

        if (email !== savedUser.email) {
            changes.email = email;
        }

        if (!Object.keys(changes).length) {
            showToast("No changes to save.");
            return;
        }

        const button = form.querySelector(
            "button[type='submit']",
        );

        setButtonBusy(button, true, "Saving…");

        try {
            const updatedUser = await updateMyProfile(changes);

            savedUser = updatedUser;

            localStorage.setItem(
                CONFIG.USER_STORAGE_KEY,
                JSON.stringify(updatedUser),
            );

            renderProfile(updatedUser);
            updateShell(updatedUser);

            setFormMessage(
                "Your profile has been updated successfully.",
                "success",
            );

            showToast("Profile updated successfully.");

        } catch (error) {
            setFormMessage(
                error.message || "Unable to update your profile.",
            );

        } finally {
            setButtonBusy(button, false, "Save Changes");
        }
    });
}