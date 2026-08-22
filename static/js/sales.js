// ==========================================
// VERA ERP - Sales Module
// Part 1
// ==========================================

document.addEventListener("DOMContentLoaded", function () {

    initializeRow(document.querySelector("#items tbody tr"));

    const btn = document.getElementById("btnAddItem");

    if (btn) {
        btn.addEventListener("click", addRow);
    }

});


// ==========================================
// Initialize Product Row
// ==========================================
function initializeRow(row) {

    const product = row.querySelector("select[name='product_id[]']");
    const qty = row.querySelector("input[name='qty[]']");
    const price = row.querySelector("input[name='price[]']");
    const info = row.querySelector(".product-info-icon");

    // Product Changed
    // Product Changed
product.addEventListener("change", function () {

    const option = this.selectedOptions[0];

    if (!option.value) {

        price.value = "0.00";
        row.querySelector(".amount").value = "0.00";

        if (info._tippy) {
            info._tippy.destroy();
        }

        info.style.display = "none";

        calculateInvoiceTotal();

        return;
    }

    // ==========================================
    // Prevent Duplicate Product
    // ==========================================

    const selectedProductId = option.value;

    const duplicate = Array.from(
        document.querySelectorAll(
            "#items tbody select[name='product_id[]']"
        )
    ).some(function (select) {

        return (
            select !== product &&
            select.value === selectedProductId
        );

    });

    if (duplicate) {

        Swal.fire({
            icon: "warning",
            title: "Product Already Added",
            text: "This product is already added to the sale. Please change the product or update the existing quantity."
        });

        // Reset current row
        product.selectedIndex = 0;

        price.value = "0.00";

        row.querySelector(".amount").value = "0.00";

        if (info._tippy) {
            info._tippy.destroy();
        }

        info.style.display = "none";

        calculateInvoiceTotal();

        return;
    }

    // ==========================================
    // Auto Fill Selling Price
    // ==========================================

    price.value = option.dataset.sprice;

    // ==========================================
    // Tooltip
    // ==========================================

    info.style.display = "inline-block";

    if (info._tippy) {
        info._tippy.destroy();
    }

    tippy(info, {
        theme: "light-border",
        allowHTML: true,
        placement: "right",
        content: `

            <table class="table table-sm mb-0">

                <tr>
                    <th>Available Stock</th>
                    <td>${option.dataset.stock}</td>
                </tr>

                <tr>
                    <th>Purchase Price</th>
                    <td>₹ ${option.dataset.pprice}</td>
                </tr>

                <tr>
                    <th>Selling Price</th>
                    <td>₹ ${option.dataset.sprice}</td>
                </tr>

                <tr>
                    <th>GST</th>
                    <td>${option.dataset.tax}%</td>
                </tr>

            </table>

        `
    });

    calculateRow(row, false);

});


    // Qty Changed
    qty.addEventListener("input", function () {

        calculateRow(row, false);

    });

    qty.addEventListener("change", function () {

        calculateRow(row, true);

    });


    // Price Changed
    price.addEventListener("input", function () {

        calculateRow(row);

    });

}



// ==========================================
// Add Row
// ==========================================
function addRow() {

    const tbody = document.querySelector("#items tbody");

    const row = tbody.rows[0].cloneNode(true);

    // Reset Product

    row.querySelector("select").selectedIndex = 0;

    // Reset Qty

    row.querySelector(".qty").value = 1;

    // Reset Price

    row.querySelector(".price").value = "0.00";

    // Reset Amount

    row.querySelector(".amount").value = "0.00";

    // Hide Tooltip

    const info = row.querySelector(".product-info-icon");

    if (info) {

        info.style.display = "none";

        if (info._tippy) {
            info._tippy.destroy();
        }

    }

    tbody.appendChild(row);

    initializeRow(row);

}



// ==========================================
// Remove Row
// ==========================================
function removeRow(btn) {

    const tbody = document.querySelector("#items tbody");

    if (tbody.rows.length === 1) {

        Swal.fire({

            icon: "warning",

            title: "Minimum one product is required."

        });

        return;

    }

    btn.closest("tr").remove();

    calculateInvoiceTotal();

}
// ==========================================
// Calculate Row
// ==========================================
function calculateRow(row, warnStock) {

    const qtyInput = row.querySelector(".qty");
    const priceInput = row.querySelector(".price");
    const amountInput = row.querySelector(".amount");
    const product = row.querySelector("select[name='product_id[]']");

    const qty = parseFloat(qtyInput.value) || 0;
    const price = parseFloat(priceInput.value) || 0;

    const option = product.selectedOptions[0];

    if (option && option.value) {

        const stock = parseFloat(option.dataset.stock) || 0;

        if (qty > stock) {

            qtyInput.classList.add("is-invalid");

            if (warnStock) {
                Swal.fire({
                    icon: "warning",
                    title: "Insufficient Stock",
                    text: `Only ${stock} item(s) available in stock.`
                });
            }

            qtyInput.value = stock;

            amountInput.value = (stock * price).toFixed(2);

            calculateInvoiceTotal();

            return;

        }

        qtyInput.classList.remove("is-invalid");

    }

    const amount = qty * price;

    amountInput.value = amount.toFixed(2);

    calculateInvoiceTotal();

}



// ==========================================
// Invoice Total
// ==========================================
// ==========================================
// Invoice Total
// ==========================================
function calculateInvoiceTotal() {

    let subtotal = 0;

    document.querySelectorAll(".amount").forEach(function (input) {

        subtotal += parseFloat(input.value) || 0;

    });

    // ==========================================
    // Discount Percentage
    // ==========================================

    const discountInput =
        document.getElementById("discount_input");

    let discountPercent = discountInput
        ? (parseFloat(discountInput.value) || 0)
        : 0;

    // Prevent negative discount
    if (discountPercent < 0) {

        discountPercent = 0;

        if (discountInput) {
            discountInput.value = "0";
        }
    }

    // Maximum discount = 100%
    if (discountPercent > 100) {

        discountPercent = 100;

        if (discountInput) {
            discountInput.value = "100";
        }

        Swal.fire({
            icon: "warning",
            title: "Invalid Discount",
            text: "Discount cannot be greater than 100%."
        });
    }

    // ==========================================
    // Calculate Discount Amount
    // ==========================================

    const discountAmount =
        (subtotal * discountPercent) / 100;

    // ==========================================
    // GST
    // ==========================================

    let gst = 0;

    document.querySelectorAll("#items tbody tr").forEach(function (row) {
        const amount = parseFloat(row.querySelector(".amount").value) || 0;
        const option = row.querySelector("select[name='product_id[]']").selectedOptions[0];
        const tax = option && option.value ? (parseFloat(option.dataset.tax) || 0) : 0;
        gst += amount * tax / 100;
    });

    // ==========================================
    // Grand Total
    // ==========================================

    const grandTotal =
        subtotal - discountAmount + gst;

    // ==========================================
    // Update Summary
    // ==========================================

    document.getElementById("subtotal").textContent =
        subtotal.toFixed(2);

    document.getElementById("discount").textContent =
        discountAmount.toFixed(2);

    document.getElementById("gst_total").textContent =
        gst.toFixed(2);

    document.getElementById("grand_total").textContent =
        grandTotal.toFixed(2);
}



// ==========================================
// Validate Before Submit
// ==========================================
const saleForm = document.querySelector("form");

if (saleForm) {

    saleForm.addEventListener("submit", function (e) {

        const rows = document.querySelectorAll("#items tbody tr");

        let valid = false;
        let incomplete = false;

        rows.forEach(function (row) {

            const product =
                row.querySelector("select[name='product_id[]']").value;

            const qty =
                parseFloat(row.querySelector(".qty").value) || 0;

            const price =
                parseFloat(row.querySelector(".price").value) || 0;

            if (!product) {
                return;
            }

            if (qty <= 0 || price <= 0) {
                incomplete = true;
                return;
            }

            valid = true;

        });

        if (incomplete || !valid) {

            e.preventDefault();

            Swal.fire({

                icon: "warning",

                title: "Incomplete Sale",

                text: "Please complete all product details before saving."

            });

            return;

        }

        e.preventDefault();

        Swal.fire({

            icon: "question",

            title: "Confirm Sale",

            text: "Do you want to save this sale?",

            showCancelButton: true,

            confirmButtonText: "Save"

        }).then((result) => {

            if (result.isConfirmed) {

                saleForm.submit();

            }

        });

    });

}



// ==========================================
// Initial Total
// ==========================================
document.addEventListener("DOMContentLoaded", function () {
    const discountInput = document.getElementById("discount_input");

    if (discountInput) {

        discountInput.addEventListener("input", function () {

        calculateInvoiceTotal();

    });

}

    calculateInvoiceTotal();

});
// ==========================================
// Cancel Sale - Unsaved Changes Confirmation
// ==========================================

document.addEventListener("DOMContentLoaded", function () {

    const cancelButton =
        document.getElementById("btnCancelSale");

    if (!cancelButton) {
        return;
    }

    cancelButton.addEventListener("click", function (e) {

        const rows =
            document.querySelectorAll("#items tbody tr");

        let hasChanges = false;

        // Check product selections
        rows.forEach(function (row) {

            const product =
                row.querySelector(
                    "select[name='product_id[]']"
                );

            const qty =
                row.querySelector(
                    "input[name='qty[]']"
                );

            const price =
                row.querySelector(
                    "input[name='price[]']"
                );

            if (
                (product && product.value) ||
                (qty && qty.value && qty.value !== "1") ||
                (price && price.value && price.value !== "0.00")
            ) {
                hasChanges = true;
            }

        });

        // Check customer
        const customer =
            document.querySelector(
                "select[name='customer_id']"
            );

        if (customer && customer.value) {
            hasChanges = true;
        }

        // Check discount
        const discount =
            document.getElementById(
                "discount_input"
            );

        if (
            discount &&
            parseFloat(discount.value || 0) !== 0
        ) {
            hasChanges = true;
        }

        // Check remarks
        const remarks =
            document.querySelector(
                "textarea[name='remarks']"
            );

        if (
            remarks &&
            remarks.value.trim() !== ""
        ) {
            hasChanges = true;
        }

        // Nothing changed → navigate directly
        if (!hasChanges) {
            return;
        }

        // Prevent immediate navigation
        e.preventDefault();

        Swal.fire({
            icon: "warning",
            title: "Discard Sale?",
            text: "You have unsaved changes. Are you sure you want to cancel?",
            showCancelButton: true,
            confirmButtonText: "Discard",
            cancelButtonText: "Stay",
            reverseButtons: true
        }).then(function (result) {

            if (result.isConfirmed) {
                window.location.href =
                    cancelButton.href;
            }

        });

    });

});