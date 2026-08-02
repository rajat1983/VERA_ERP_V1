function initializeCommonFeatures() {

    const dateFields = [
        "sale_date",
        "purchase_date",
        "invoice_date",
        "payment_date"
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

});