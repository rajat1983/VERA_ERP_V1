(function () {
    const search = document.getElementById("category_search");
    const hidden = document.getElementById("category");
    const results = document.getElementById("category_results");
    const modalEl = document.getElementById("quickCategoryModal");
    if (!search || !hidden || !results) {
        return;
    }

    const csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
    let timer = null;
    let latest = "";
    let items = [];
    let activeIndex = -1;

    function hide() {
        results.hidden = true;
        results.innerHTML = "";
        search.setAttribute("aria-expanded", "false");
        activeIndex = -1;
        items = [];
    }

    function highlight() {
        results.querySelectorAll("[data-suggest-index]").forEach(function (row, i) {
            row.classList.toggle("is-highlighted", i === activeIndex);
        });
    }

    function selectCategory(name) {
        hidden.value = name;
        search.value = name;
        hide();
    }

    function openAdd(prefill) {
        hide();
        const input = document.getElementById("quick_category_name");
        if (input) {
            input.value = (prefill || "").trim();
        }
        if (modalEl && window.bootstrap) {
            window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
            setTimeout(function () {
                if (input) input.focus();
            }, 200);
        }
    }

    function render(query, matches) {
        results.innerHTML = "";
        items = matches || [];
        items.forEach(function (row, index) {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "customer-suggest-item";
            btn.setAttribute("data-suggest-index", String(index));
            btn.textContent = row.name;
            btn.addEventListener("mousedown", function (e) {
                e.preventDefault();
                selectCategory(row.name);
            });
            results.appendChild(btn);
        });
        const add = document.createElement("button");
        add.type = "button";
        add.className = "customer-suggest-item customer-suggest-add";
        add.setAttribute("data-suggest-index", String(items.length));
        add.textContent = "+ Add New Category";
        add.addEventListener("mousedown", function (e) {
            e.preventDefault();
            openAdd(query);
        });
        results.appendChild(add);
        items = items.concat([{ type: "add" }]);
        results.hidden = false;
        search.setAttribute("aria-expanded", "true");
        activeIndex = 0;
        highlight();
    }

    function fetchMatches(query) {
        latest = query;
        fetch("/products/categories?q=" + encodeURIComponent(query))
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (query !== latest) return;
                render(query, Array.isArray(data) ? data : []);
            })
            .catch(function () {
                render(query, []);
            });
    }

    search.addEventListener("focus", function () {
        fetchMatches(search.value.trim());
    });

    search.addEventListener("input", function () {
        hidden.value = search.value.trim();
        clearTimeout(timer);
        timer = setTimeout(function () {
            fetchMatches(search.value.trim());
        }, 180);
    });

    search.addEventListener("keydown", function (e) {
        if (results.hidden) return;
        const max = items.length - 1;
        if (e.key === "ArrowDown") {
            e.preventDefault();
            activeIndex = activeIndex < max ? activeIndex + 1 : 0;
            highlight();
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            activeIndex = activeIndex > 0 ? activeIndex - 1 : max;
            highlight();
        } else if (e.key === "Enter") {
            if (activeIndex < 0 || !items[activeIndex]) return;
            e.preventDefault();
            const chosen = items[activeIndex];
            if (chosen.type === "add") {
                openAdd(search.value.trim());
            } else {
                selectCategory(chosen.name);
            }
        } else if (e.key === "Escape") {
            hide();
        }
    });

    search.addEventListener("blur", function () {
        setTimeout(hide, 150);
    });

    const saveBtn = document.getElementById("quickCategorySave");
    if (saveBtn) {
        saveBtn.addEventListener("click", function () {
            const name = (document.getElementById("quick_category_name").value || "").trim();
            if (!name) {
                Swal.fire({ icon: "warning", title: "Category name is required." });
                return;
            }
            saveBtn.disabled = true;
            fetch("/products/categories/quick-add", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                    "X-CSRF-Token": csrf
                },
                body: JSON.stringify({ name: name, csrf_token: csrf })
            })
                .then(function (res) { return res.json().then(function (body) { return { ok: res.ok, body: body }; }); })
                .then(function (payload) {
                    saveBtn.disabled = false;
                    if (!payload.body || !payload.body.ok) {
                        Swal.fire({
                            icon: "error",
                            title: "Could not save category",
                            text: (payload.body && payload.body.error) || "Please try again."
                        });
                        return;
                    }
                    if (modalEl && window.bootstrap) {
                        window.bootstrap.Modal.getOrCreateInstance(modalEl).hide();
                    }
                    selectCategory(payload.body.name);
                })
                .catch(function () {
                    saveBtn.disabled = false;
                    Swal.fire({ icon: "error", title: "Could not save category" });
                });
        });
    }
})();
