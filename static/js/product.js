// =======================================================
// VERA ERP - Product Module
// product.js
// =======================================================


// -------------------------------------------------------
// Global Variables
// -------------------------------------------------------

let input = null;
let hidden = null;
let listBox = null;

let costPrice = null;
let sellingPrice = null;

let imageInput = null;
let saveButton = null;
let continueButton = null;

let form = null;


// =======================================================
// Page Initialization
// =======================================================

document.addEventListener("DOMContentLoaded", function () {

    initializeProductModule();

});


// =======================================================
// Initialize Product Module
// =======================================================

function initializeProductModule() {

    console.log("Initializing Product Module...");

    // ---------------------------------------------
    // Form
    // ---------------------------------------------

    form = document.querySelector("form");

    // ---------------------------------------------
    // Vendor
    // ---------------------------------------------

    input = document.getElementById("vendor_input");
    hidden = document.getElementById("vendor_id");
    listBox = document.getElementById("vendor_suggestions");

    // ---------------------------------------------
    // Pricing
    // ---------------------------------------------

    costPrice = document.getElementById("cost_price");
    sellingPrice = document.getElementById("selling_price");

    // ---------------------------------------------
    // Image
    // ---------------------------------------------

    imageInput = document.getElementById("image");

    // ---------------------------------------------
    // Buttons
    // ---------------------------------------------

    saveButton = document.getElementById("btnSaveProduct");
    continueButton = document.getElementById("btnContinueSave");

    registerEvents();

}
// =======================================================
// Register Events
// =======================================================

function registerEvents() {

    // ---------------------------
    // Image Preview
    // ---------------------------

    if (imageInput) {

        imageInput.addEventListener("change", function () {

            previewProductImage(this);

        });

    }

    // ---------------------------
    // Profit Calculator
    // ---------------------------

    if (costPrice) {

        costPrice.addEventListener("input", calculateMargin);

    }

    if (sellingPrice) {

        sellingPrice.addEventListener("input", calculateMargin);

    }

    // ---------------------------
    // Save Product
    // ---------------------------

    if (saveButton) {

        saveButton.addEventListener("click", validateSellingPrice);

    }

    // ---------------------------
    // Continue Save
    // ---------------------------

    // if (continueButton) {

    //     continueButton.addEventListener("click", submitProduct);

    // }

    // ---------------------------
    // Vendor Search
    // ---------------------------

    if (input) {

        input.addEventListener("keyup", searchVendor);

    }

    // ---------------------------
    // Form Validation
    // ---------------------------

    if (form) {

        form.addEventListener("submit", validateVendorSelection);

    }

    // ---------------------------
    // Initial Profit Calculation
    // ---------------------------

    if (costPrice && sellingPrice) {

        calculateMargin();

    }

}
// =======================================================
// Product Image Preview
// =======================================================

function previewProductImage(fileInput) {

    if (!fileInput.files || !fileInput.files[0]) {

        return;

    }

    const reader = new FileReader();

    reader.onload = function (e) {

        const preview = document.getElementById("previewImage");

        if (!preview) {

            return;

        }

        preview.innerHTML = `

            <img
                src="${e.target.result}"
                class="img-thumbnail"
                style="width:180px;
                       height:180px;
                       object-fit:cover;">

        `;

    };

    reader.readAsDataURL(fileInput.files[0]);

}


// =======================================================
// Profit Calculator
// =======================================================

function calculateMargin() {

    if (!costPrice || !sellingPrice) {

        return;

    }

    const cost = parseFloat(costPrice.value) || 0;

    const selling = parseFloat(sellingPrice.value) || 0;

    const profit = selling - cost;

    let margin = 0;

    if (cost > 0) {

        margin = (profit / cost) * 100;

    }

    const marginBox = document.getElementById("profit_margin");

    if (!marginBox) {

        return;

    }

    marginBox.value =
        "₹ " +
        profit.toFixed(2) +
        " (" +
        margin.toFixed(2) +
        "%)";

}


// =======================================================
// Selling Price Validation
// =======================================================

function validateSellingPrice() {

    // Vendor Validation
    if (!hidden || hidden.value.trim() === "") {

        alert("Please select a Vendor.");

        return;

    }

    const cost = parseFloat(costPrice.value) || 0;
    const selling = parseFloat(sellingPrice.value) || 0;

    if (selling < cost) {

        const modal = new bootstrap.Modal(
            document.getElementById("priceWarningModal")
        );

        modal.show();

        return;
    }

    // Submit
    if (form) {
        form.requestSubmit();
    }

}


// =======================================================
// Final Submit
// =======================================================

// function submitProduct() {

//     const submitButton =
//         document.getElementById("realSubmit");

//     if (!submitButton) {

//         return;

//     }

//     submitButton.click();

// }
// =======================================================
// Vendor Search
// =======================================================

async function searchVendor() {

    if (!input || !hidden || !listBox) {

        return;

    }

    const q = input.value.trim();

    listBox.innerHTML = "";

    hidden.value = "";

    if (q === "") {

        return;

    }

    try {

        const response = await fetch(
            `/api/vendors/search?q=${encodeURIComponent(q)}`
        );

        const vendors = await response.json();

        if (vendors.length > 0) {

            vendors.forEach(vendor => {

                const btn = document.createElement("button");

                btn.type = "button";

                btn.className =
                    "list-group-item list-group-item-action";

                btn.innerHTML = `
                    <i class="bi bi-building"></i>
                    ${vendor.name}
                `;

                btn.addEventListener("click", function () {

                    input.value = vendor.name;

                    hidden.value = vendor.id;

                    listBox.innerHTML = "";

                });

                listBox.appendChild(btn);

            });

        }

        else {

            showAddVendorOption(q);

        }

    }

    catch (error) {

        console.error("Vendor Search Error :", error);

    }

}



// =======================================================
// Add Vendor Option
// =======================================================

function showAddVendorOption(name) {

    const btn = document.createElement("button");

    btn.type = "button";

    btn.className =
        "list-group-item list-group-item-action text-success";

    btn.innerHTML = `
        <i class="bi bi-plus-circle"></i>
        Add "${name}"
    `;

    btn.addEventListener("click", function () {

        createVendor(name);

    });

    listBox.appendChild(btn);

}



// =======================================================
// Create Vendor
// =======================================================

async function createVendor(name) {

    if (!confirm(`Create Vendor "${name}" ?`)) {

        return;

    }

    try {

        const response = await fetch("/api/vendors/add", {

            method: "POST",

            headers: {

                "Content-Type": "application/json"

            },

            body: JSON.stringify({

                name: name

            })

        });

        const vendor = await response.json();

        input.value = vendor.name;

        hidden.value = vendor.id;

        listBox.innerHTML = "";

    }

    catch (error) {

        console.error(error);

        alert("Unable to create vendor.");

    }

}



// =======================================================
// Vendor Validation
// =======================================================

function validateVendorSelection(event) {

    if (!hidden) {
        return;
    }

    if (hidden.value.trim() === "") {

        event.preventDefault();

        alert("Please select a Vendor.");

        return false;

    }

    return true;

}