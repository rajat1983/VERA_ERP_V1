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

    //console.log("Initializing Product Module...");
    
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

        saveButton.addEventListener("click", function () {
            const action = document.getElementById("product_action");
            if (action) {
                action.value = "create";
            }
            validateSellingPrice();
        });

    }

    if (continueButton) {

        continueButton.addEventListener("click", function () {
            const action = document.getElementById("product_action");
            if (action) {
                action.value = "another";
            }
            validateSellingPrice();
        });

    }

   

     // Vendor Search
    const vendorInput = document.getElementById("vendor_input");

    if (vendorInput) {
        vendorInput.addEventListener("keyup", searchVendor);
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

    const categoryField = document.getElementById("category");
    if (categoryField && !categoryField.value.trim()) {
        alert("Please select a Category.");
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

    const input = document.getElementById("vendor_input");
    const list = document.getElementById("vendor_suggestions");

    const q = input.value.trim();

    list.innerHTML = "";

    if (q.length < 2) {
        return;
    }

    const response = await fetch(
        `/api/vendors/search?q=${encodeURIComponent(q)}`
    );

    const vendors = await response.json();

    if (!vendors.length) {

        list.innerHTML = `
            <button
                type="button"
                class="list-group-item list-group-item-action text-danger">
                No Vendor Found
            </button>
        `;

        return;
    }

    vendors.forEach(v => {

        const btn = document.createElement("button");

        btn.type = "button";

        btn.className =
            "list-group-item list-group-item-action";

        btn.innerHTML = `
            <strong>${v.vendor_code}</strong><br>
            <small>${v.name}</small>
        `;

        btn.onclick = function () {

            input.value = `${v.vendor_code} - ${v.name}`;

            document.getElementById("vendor_id").value = v.id;

            list.innerHTML = "";

        };

        list.appendChild(btn);

    });

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