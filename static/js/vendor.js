function confirmVendorCancel(url) {

    Swal.fire({

        title: "Cancel?",

        text: "Any unsaved changes will be lost.",

        icon: "warning",

        showCancelButton: true,

        confirmButtonText: "Yes",

        cancelButtonText: "No"

    }).then((result) => {

        if (result.isConfirmed) {

            window.location.href = url;

        }

    });

}

function autoSearchVendor() {

    const q = document.getElementById("vendorSearch").value;

    fetch("/vendor-search?q=" + encodeURIComponent(q))

        .then(response => response.json())

        .then(data => {

            let rows = "";

            if (data.length === 0) {

                rows = `

                    <tr>

                        <td colspan="9" class="text-center py-4 text-danger fw-bold">

                            <i class="bi bi-search me-2"></i>

                            No Record Found

                        </td>

                    </tr>

                `;

            } else {

                data.forEach((vr, index) => {

                    rows += `

                        <tr>

                            <td>${index + 1}</td>

                            <td><strong>${vr.vendor_code ?? "-"}</strong></td>

                            <td>${vr.name ?? "-"}</td>

                            <td>${vr.phone ?? "-"}</td>

                            <td>${vr.email ?? "-"}</td>

                            <td>${vr.gst_number ?? "-"}</td>

                            <td>${vr.city ?? "-"}</td>

                            <td class="text-center">

                                ${
                                    vr.status.toLowerCase() === "active"

                                    ? '<span class="badge bg-success">Active</span>'

                                    : '<span class="badge bg-danger">Inactive</span>'
                                }

                            </td>

                            <td class="text-center">

                                <a href="/vendors/view/${vr.id}"
                                   class="btn btn-info btn-sm"
                                   title="View">

                                    <i class="bi bi-eye"></i>

                                </a>

                                <a href="/vendors/edit/${vr.id}"
                                   class="btn btn-warning btn-sm"
                                   title="Edit">

                                    <i class="bi bi-pencil-square"></i>

                                </a>

                                <button
                                    type="button"
                                    class="btn btn-danger btn-sm"
                                    onclick="confirmVendorDelete(${vr.id})"
                                    title="Delete">

                                    <i class="bi bi-trash"></i>

                                </button>

                            </td>

                        </tr>

                    `;

                });

            }

            document.getElementById("vendorTable").innerHTML = rows;

        })

        .catch(error => {

            console.error(error);

        });

}
function confirmVendorSubmit(event) {

    event.preventDefault();

    const form = document.getElementById("vendorForm");

    // Run browser validation first
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const isEdit = form.dataset.mode === "edit";

    Swal.fire({
        title: isEdit ? "Update Vendor?" : "Save Vendor?",
        text: isEdit
            ? "Do you want to update this vendor?"
            : "Do you want to save this vendor?",
        icon: "question",
        showCancelButton: true,
        confirmButtonText: isEdit ? "Yes, Update" : "Yes, Save",
        cancelButtonText: "Cancel"
    }).then((result) => {

        if (result.isConfirmed) {
            form.submit();
        }

    });

}
function searchVendor() {

    const q = document.getElementById("vendorSearch").value;

    fetch(`/vendor/auto-search?q=${encodeURIComponent(q)}`)

    .then(response => response.json())

    .then(rows => {

        let html = "";

        rows.forEach((v, index) => {

            html += `

            <tr>

                <td>${index + 1}</td>

                <td><strong>${v.vendor_code ?? "-"}</strong></td>

                <td>${v.name}</td>

                <td>${v.phone ?? "-"}</td>

                <td>${v.email ?? "-"}</td>

                <td>${v.gst_number ?? "-"}</td>

                <td>${v.city ?? "-"}</td>

                <td class="text-center">

                    ${
                        v.status.toLowerCase() === "active"

                        ? '<span class="badge bg-success">Active</span>'

                        : '<span class="badge bg-danger">Inactive</span>'
                    }

                </td>

                <td class="text-center">

                    <a
                        href="/vendor/view/${v.id}"
                        class="btn btn-info btn-sm"
                        title="View">

                        <i class="bi bi-eye"></i>

                    </a>

                    <a
                        href="/vendor/edit/${v.id}"
                        class="btn btn-warning btn-sm"
                        title="Edit">

                        <i class="bi bi-pencil-square"></i>

                    </a>

                    <button
                        type="button"
                        class="btn btn-danger btn-sm"
                        onclick="confirmVendorDelete(${v.id})">

                        <i class="bi bi-trash"></i>

                    </button>

                </td>

            </tr>

            `;

        });

        if (rows.length === 0) {

            html = `

            <tr>

                <td colspan="9" class="text-center text-muted">

                    No vendors found.

                </td>

            </tr>

            `;

        }

        document.getElementById("vendorTable").innerHTML = html;

    });

}


// ==========================================
// Delete Confirmation
// ==========================================

function confirmVendorDelete(id) {

    Swal.fire({

        title: "Delete Vendor?",

        text: "This action cannot be undone.",

        icon: "warning",

        showCancelButton: true,

        confirmButtonColor: "#dc3545",

        confirmButtonText: "Delete",

        cancelButtonText: "Cancel"

    }).then((result) => {

        if (result.isConfirmed) {

            window.location.href = "/vendor/delete/" + id;

        }

    });

}
