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

document.addEventListener("DOMContentLoaded", function () {

    initializeCommonFeatures();

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