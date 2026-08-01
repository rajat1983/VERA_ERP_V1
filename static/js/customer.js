// ========================================
// Customer Module JavaScript
// ========================================

document.addEventListener("DOMContentLoaded", function () {

    initializeCustomer();

});

// ========================================
// Initialize
// ========================================

function initializeCustomer() {

    bindPhoneValidation();

    bindEmailValidation();

    bindGSTValidation();

    bindPinValidation();

}
// ========================================
// Phone Validation
// ========================================

function bindPhoneValidation() {

    const phone = document.querySelector("input[name='phone']");

    if (!phone)
        return;

    phone.addEventListener("input", function () {

        this.value = this.value.replace(/\D/g, "");

        if (this.value.length > 10) {

            this.value = this.value.substring(0, 10);

        }

    });

}
// ========================================
// Email Validation
// ========================================

function bindEmailValidation() {

    const email = document.querySelector("input[name='email']");

    if (!email)
        return;

    email.addEventListener("blur", function () {

        if (!this.value)
            return;

        const regex =
            /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!regex.test(this.value)) {

            Swal.fire({

                icon: "warning",

                title: "Invalid Email",

                text: "Please enter a valid email address."

            });

            

        }

    });

}// ========================================
// GST Uppercase
// ========================================

function bindGSTValidation() {

    const gst = document.querySelector("input[name='gst_no']");

    if (!gst)
        return;

    gst.addEventListener("input", function () {

        this.value = this.value.toUpperCase();

    });

}
// ========================================
// PIN Validation
// ========================================

function bindPinValidation() {

    const pin = document.querySelector("input[name='pincode']");

    if (!pin)
        return;

    pin.addEventListener("input", function () {

        this.value = this.value.replace(/\D/g, "");

        if (this.value.length > 6) {

            this.value = this.value.substring(0, 6);

        }

    });

}
// ========================================
// Save / Update Confirmation
// ========================================

function confirmCustomerSubmit(event) {

    event.preventDefault();

    const form = document.getElementById("customerForm");

    Swal.fire({

        title: form.dataset.mode === "edit"
            ? "Update Customer?"
            : "Save Customer?",

        text: form.dataset.mode === "edit"
            ? "Do you want to update this customer?"
            : "Do you want to save this customer?",

        icon: "question",

        showCancelButton: true,

        confirmButtonText: form.dataset.mode === "edit"
            ? "Yes, Update"
            : "Yes, Save",

        cancelButtonText: "Cancel"

    }).then((result) => {

        if (!result.isConfirmed)
            return;

        // Validation after confirmation
        if (!form.checkValidity()) {

            form.reportValidity();

            return;

        }

        form.submit();

    });

}
// ========================================
// Cancel Confirmation
// ========================================

function confirmCustomerCancel(url) {

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