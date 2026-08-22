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

                            <td class="text-center text-nowrap">

                                <div class="d-inline-flex flex-nowrap align-items-center gap-1">

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

                                </div>

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
async function searchVendor() {

    const input = document.getElementById("vendor_input");
    const hidden = document.getElementById("vendor_id");
    const list = document.getElementById("vendor_suggestions");

    const q = input.value.trim();

    list.innerHTML = "";

    if (q.length < 2) {
        return;
    }

    try {

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
                <strong>${v.vendor_code ?? ""}</strong>
                ${v.vendor_code ? " - " : ""}
                ${v.name}
            `;

            btn.onclick = function () {

                input.value = `${v.vendor_code ?? ""} ${v.name}`.trim();

                hidden.value = v.id;

                list.innerHTML = "";

            };

            list.appendChild(btn);

        });

    } catch (err) {

        console.error(err);

    }

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
