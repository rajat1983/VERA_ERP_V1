function initializeCommonFeatures() {

    const dateFields = [
        "sale_date",
        "purchase_date",
        "invoice_date",
        "payment_date",
        "batch_date"
    ];

    dateFields.forEach(function(id) {

        const field = document.getElementById(id);

        if (field && field.value === "") {

            const today = new Date();

            field.value = today.toISOString().split("T")[0];

        }

    });

}

function veraShowDenied() {
    if (window.Swal) {
        Swal.fire({
            icon: "warning",
            title: "Permission denied",
            text: "You do not have permission for that action.",
            confirmButtonText: "OK"
        });
    } else {
        alert("Permission denied");
    }
}

function veraPathAllowed(path, method) {
    method = (method || "GET").toUpperCase();
    const can = window.veraCan || {};
    const role = (window.veraRole || "").toLowerCase();
    path = (path || "").split("?")[0];
    if (can.admin || !role) {
        return true;
    }
    if (path === "/profile" || path.indexOf("/profile") === 0) {
        return true;
    }
    if (path.indexOf("/admin") === 0 || path.indexOf("/users") === 0 || path.indexOf("/settings") === 0) {
        return false;
    }
    if (path.indexOf("/delete") !== -1 || path.indexOf("/cancel/") !== -1) {
        return false;
    }
    if (role === "manager") {
        return true;
    }
    if (method === "GET" || method === "HEAD") {
        if (path === "/sales/add" || /^\/sales\/\d+\/edit$/.test(path)) {
            return true;
        }
        if (path === "/add" || path === "/create" || path === "/update" || path.indexOf("/edit/") === 0) {
            return false;
        }
        if (/^\/services\/\d+\/edit$/.test(path)) {
            return false;
        }
        const blocked = [
            "/customer/add",
            "/customer/edit",
            "/vendors/add",
            "/vendors/edit",
            "/products/add",
            "/products/edit",
            "/services/add",
            "/purchases/add",
            "/purchases/edit",
            "/production/add",
            "/stock/adjust",
            "/settings",
            "/admin",
            "/users"
        ];
        for (let i = 0; i < blocked.length; i += 1) {
            if (path === blocked[i] || path.indexOf(blocked[i]) === 0) {
                return false;
            }
        }
        return true;
    }
    if (method === "POST" && (path === "/sales/add" || path === "/sales/quick-customer" || path === "/pos/complete" || path === "/pos/session/start" || /^\/sales\/\d+\/update$/.test(path))) {
        return true;
    }
    return false;
}

function veraEscapeHtml(value) {
    return String(value == null ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function veraCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
}

function veraSubmitPost(url) {
    const form = document.createElement("form");
    form.method = "POST";
    form.action = url;
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = "csrf_token";
    input.value = veraCsrfToken();
    form.appendChild(input);
    document.body.appendChild(form);
    form.submit();
}

function veraConfirmPost(url, title, text) {
    if (window.veraPathAllowed && !window.veraPathAllowed(url, "POST")) {
        veraShowDenied();
        return;
    }
    const run = function () {
        veraSubmitPost(url);
    };
    if (window.Swal) {
        Swal.fire({
            title: title || "Delete?",
            text: text || "This cannot be undone.",
            icon: "warning",
            showCancelButton: true,
            confirmButtonColor: "#dc3545",
            confirmButtonText: "Delete",
            cancelButtonText: "Cancel"
        }).then(function (result) {
            if (result.isConfirmed) {
                run();
            }
        });
    } else if (window.confirm(title || "Delete?")) {
        run();
    }
}

window.veraShowDenied = veraShowDenied;
window.veraPathAllowed = veraPathAllowed;
window.veraEscapeHtml = veraEscapeHtml;
window.veraConfirmPost = veraConfirmPost;

document.addEventListener("click", function (e) {
    const a = e.target.closest("a[href]");
    if (!a) {
        return;
    }
    const href = a.getAttribute("href") || "";
    if (!href || href.charAt(0) === "#" || href.indexOf("javascript:") === 0) {
        return;
    }
    if (a.target && a.target !== "_self") {
        return;
    }
    let url;
    try {
        url = new URL(a.href, window.location.href);
    } catch (err) {
        return;
    }
    if (url.origin !== window.location.origin) {
        return;
    }
    if (veraPathAllowed(url.pathname, "GET")) {
        return;
    }
    e.preventDefault();
    e.stopPropagation();
    veraShowDenied();
}, true);

document.addEventListener("submit", function (e) {
    const form = e.target;
    if (!form || form.tagName !== "FORM") {
        return;
    }
    const method = (form.getAttribute("method") || "get").toUpperCase();
    if (method === "GET") {
        return;
    }
    let url;
    try {
        url = new URL(form.action || window.location.href, window.location.href);
    } catch (err) {
        return;
    }
    if (url.origin !== window.location.origin) {
        return;
    }
    if (veraPathAllowed(url.pathname, method)) {
        return;
    }
    e.preventDefault();
    e.stopPropagation();
    veraShowDenied();
}, true);

document.addEventListener("DOMContentLoaded", function () {

    initializeCommonFeatures();

    if (sessionStorage.getItem("veraDenied") === "1") {
        sessionStorage.removeItem("veraDenied");
        veraShowDenied();
    }

    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) {
        document.querySelectorAll("form").forEach(function (form) {
            const method = (form.getAttribute("method") || "get").toLowerCase();
            if (method !== "post") return;
            if (form.querySelector("input[name='csrf_token']")) return;
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = "csrf_token";
            input.value = meta.content;
            form.appendChild(input);
        });
    }

});
