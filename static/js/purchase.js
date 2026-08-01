// ========================================
// Purchase Module JavaScript
// ========================================

document.addEventListener("DOMContentLoaded", function () {

    initializePurchase();

});

// ========================================
// Initialize
// ========================================

function initializePurchase() {

    bindRemoveRow();
    bindProductSelection();
    calculateTotals();
    bindEnterNavigation();

}

// ========================================
// Add Product Row
// ========================================

function addRow() {

    const table = document.getElementById("items_table");

    const firstRow = table.rows[0];

    const newRow = firstRow.cloneNode(true);

    newRow.querySelectorAll("input").forEach(input => {
        input.value = "";
    });

    newRow.querySelectorAll("select").forEach(select => {
        select.selectedIndex = 0;
    });

    newRow.querySelector(".line-total").value = "0.00";

    table.appendChild(newRow);

    calculateTotals();

    // Focus on Product dropdown
    newRow.querySelector(".product").focus();

}
function bindEnterNavigation() {

    document.addEventListener("keydown", function (e) {

        if (e.key !== "Enter")
            return;

        const row = e.target.closest("tr");

        if (!row)
            return;

        e.preventDefault();

        if (e.target.classList.contains("product")) {

            row.querySelector(".qty").focus();

        }

        else if (e.target.classList.contains("qty")) {

            row.querySelector(".price").focus();

        }

        else if (e.target.classList.contains("price")) {

            const rows = document.querySelectorAll("#items_table tr");

            const isLastRow = row === rows[rows.length - 1];

            if (isLastRow) {

                addRow();

            } else {

                row.nextElementSibling.querySelector(".product").focus();

            }

        }

    });

}

// ========================================
// Remove Row
// ========================================

// function bindRemoveRow() {

//     document.addEventListener("click", function (e) {

//         if (!e.target.classList.contains("remove-row"))
//             return;

//         const rows = document.querySelectorAll("#items_table tr");

//         if (rows.length === 1) {

//             alert("At least one item is required.");

//             return;

//         }

//         e.target.closest("tr").remove();

//     });

// }
function calculateTotals() {

    let grandTotal = 0;

    document.querySelectorAll("#items_table tr").forEach(row => {

        const qty =
            parseFloat(row.querySelector(".qty").value) || 0;

        const price =
            parseFloat(row.querySelector(".price").value) || 0;

        const total = qty * price;

        row.querySelector(".line-total").value =
            total.toFixed(2);

        grandTotal += total;

    });

    document.getElementById("grandTotal").innerText =
        grandTotal.toFixed(2);

}

document.addEventListener("input", function(e){

    if(
        e.target.classList.contains("qty") ||
        e.target.classList.contains("price")
    ){

        calculateTotals();

    }

});
// ========================================
// Remove Row
// ========================================

function bindRemoveRow() {

    document.addEventListener("click", function (e) {

        if (!e.target.classList.contains("remove-row"))
            return;

        const rows = document.querySelectorAll("#items_table tr");

        if (rows.length === 1) {

            alert("At least one item is required.");
            return;

        }

        Swal.fire({
    title: "Remove Item?",
    text: "Do you want to remove this product from the purchase?",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Yes, Remove",
    cancelButtonText: "Cancel"

    }).then((result) => {

        if (result.isConfirmed) {

            e.target.closest("tr").remove();

            calculateTotals();

        }

    });

        // Recalculate Grand Total
        calculateTotals();

    });

}
// ========================================
// Product Change
// ========================================

function bindProductSelection() {

    document.addEventListener("change", function (e) {

        if (!e.target.classList.contains("product"))
            return;

        if (!validateDuplicateProducts(e.target))
            return;

        const row = e.target.closest("tr");

        const selected = e.target.options[e.target.selectedIndex];

        const price = selected.dataset.price || 0;

        row.querySelector(".price").value = price;

        calculateTotals();

    });

}

    // ========================================
// Prevent Duplicate Products
// ========================================

function validateDuplicateProducts(currentSelect) {

    const selectedValue = currentSelect.value;

    if (!selectedValue) return true;

    const selects = document.querySelectorAll(".product");

    let count = 0;

    selects.forEach(select => {

        if (select.value === selectedValue) {
            count++;
        }

    });

    if (count > 1) {

        alert("This product has already been added.");

        currentSelect.value = "";

        const row = currentSelect.closest("tr");

        row.querySelector(".price").value = "";
        row.querySelector(".qty").value = "";
        row.querySelector(".line-total").value = "0.00";

        calculateTotals();

        return false;
    }

    return true;
}
// ==========================================
// Save Purchase Confirmation
// ==========================================

function confirmPurchaseSubmit(event) {

    event.preventDefault();

    const isEdit = window.location.pathname.includes("/edit/");

    Swal.fire({
        title: isEdit ? "Update Purchase?" : "Save Purchase?",
        text: isEdit
            ? "Do you want to update this purchase?"
            : "Do you want to save this purchase?",
        icon: "question",
        showCancelButton: true,
        confirmButtonText: isEdit ? "Yes, Update" : "Yes, Save",
        cancelButtonText: "Cancel"

    }).then((result) => {

        if (result.isConfirmed) {

            document.getElementById("purchaseForm").submit();

        }

    });

}


// ==========================================
// Cancel Confirmation
// ==========================================

function confirmPurchaseCancel(url) {

    Swal.fire({
        title: "Cancel?",
        text: "Unsaved changes will be lost.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Yes",
        cancelButtonText: "Continue Editing"

    }).then((result) => {

        if (result.isConfirmed) {

            window.location.href = url;

        }

    });

}
