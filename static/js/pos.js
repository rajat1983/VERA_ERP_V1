(function () {
    const root = document.getElementById("posApp");
    if (!root) return;

    const csrf = root.dataset.csrf || (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
    let categories = [];
    try {
        categories = JSON.parse(root.dataset.categories || "[]");
    } catch (err) {
        categories = [];
    }
    let kind = "product";
    let category = "";
    let cart = [];
    let payMode = "cash";
    let daySession = null;
    try {
        daySession = JSON.parse(root.dataset.session || "null");
    } catch (err) {
        daySession = null;
    }

    const els = {
        search: document.getElementById("posSearch"),
        cats: document.getElementById("posCats"),
        grid: document.getElementById("posGrid"),
        quick: document.getElementById("posQuick"),
        lines: document.getElementById("posCartLines"),
        count: document.getElementById("posCartCount"),
        subtotal: document.getElementById("posSubtotal"),
        tax: document.getElementById("posTax"),
        grand: document.getElementById("posGrand"),
        discount: document.getElementById("posDiscount"),
        dayBtn: document.getElementById("posDayBtn"),
        hint: document.getElementById("posHint"),
        complete: document.getElementById("posComplete"),
        splitBox: document.getElementById("posSplitBox"),
        splitCash: document.getElementById("splitCash"),
        splitUpi: document.getElementById("splitUpi")
    };

    function money(n) {
        return "₹ " + (Number(n) || 0).toFixed(2);
    }

    function headers() {
        return {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRF-Token": csrf
        };
    }

    function lineKey(item) {
        if (item.product_id) return item.item_type + ":" + item.product_id;
        return "quick:" + item.name + ":" + item.price;
    }

    function totals() {
        let subtotal = 0;
        let gst = 0;
        cart.forEach(function (line) {
            const amount = line.qty * line.price;
            subtotal += amount;
            gst += amount * (line.tax_rate || 0) / 100;
        });
        let discount = Number(els.discount.value || 0);
        if (discount < 0) discount = 0;
        if (discount > subtotal) discount = subtotal;
        return {
            subtotal: subtotal,
            discount: discount,
            gst: gst,
            grand: Math.max(0, subtotal - discount + gst)
        };
    }

    function dayOpen() {
        return !!(daySession && daySession.id);
    }

    function renderDay() {
        if (dayOpen()) {
            els.dayBtn.textContent = "Day started";
            els.dayBtn.classList.add("is-open");
            els.hint.textContent = "";
            els.complete.disabled = cart.length === 0;
        } else {
            els.dayBtn.textContent = "Day not started — click to start";
            els.dayBtn.classList.remove("is-open");
            els.hint.textContent = "Start the business day first.";
            els.complete.disabled = true;
        }
    }

    function renderCats(list) {
        els.cats.innerHTML = "";
        const all = document.createElement("button");
        all.type = "button";
        all.className = "pos-cat" + (category ? "" : " is-on");
        all.textContent = "All";
        all.addEventListener("click", function () {
            category = "";
            renderCats(list);
            loadCatalog();
        });
        els.cats.appendChild(all);
        (list || []).forEach(function (name) {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "pos-cat" + (category === name ? " is-on" : "");
            btn.textContent = name;
            btn.addEventListener("click", function () {
                category = name;
                renderCats(list);
                loadCatalog();
            });
            els.cats.appendChild(btn);
        });
    }

    function cardHtml(p) {
        const isService = p.product_type === "service";
        const img = p.image
            ? '<img src="/static/uploads/products/' + encodeURIComponent(p.image) + '" alt="">'
            : (isService ? '<i class="bi bi-briefcase"></i>' : '<i class="bi bi-box-seam"></i>');
        const out = !isService && p.stock_qty <= 0;
        const meta = isService ? escapeHtml(p.category || p.unit || "") : ("SKU: " + escapeHtml(p.sku || "—"));
        const pack = isService ? escapeHtml(p.unit || "") : (out ? "Out of stock" : (p.stock_qty + " " + (p.unit || "pcs")));
        return (
            '<article class="pos-card" data-id="' + p.id + '">' +
            '<div class="pos-card-icon">' + img + "</div>" +
            "<h3>" + escapeHtml(p.name) + "</h3>" +
            '<div class="pos-sku">' + meta + "</div>" +
            '<div class="d-flex justify-content-between align-items-baseline">' +
            '<span class="pos-price">' + money(p.price) + "</span>" +
            '<span class="pos-pack">' + pack + "</span>" +
            "</div>" +
            '<div class="pos-card-actions">' +
            '<div class="pos-stepper"><button type="button" data-act="minus">-</button><span data-qty>1</span><button type="button" data-act="plus">+</button></div>' +
            '<button type="button" class="pos-add" data-act="add"' + (out ? " disabled" : "") + ">Add</button>" +
            "</div></article>"
        );
    }

    function bindCards(products) {
        els.grid.querySelectorAll(".pos-card").forEach(function (card, i) {
            const p = products[i];
            const qtyEl = card.querySelector("[data-qty]");
            card.addEventListener("click", function (e) {
                const act = e.target.getAttribute("data-act");
                if (!act) return;
                let qty = parseInt(qtyEl.textContent, 10) || 1;
                if (act === "minus") qty = Math.max(1, qty - 1);
                if (act === "plus") qty = Math.min(Math.max(1, p.stock_qty || 1), qty + 1);
                qtyEl.textContent = String(qty);
                if (act === "add") addToCart({
                    product_id: p.id,
                    item_type: kind === "service" ? "service" : "product",
                    name: p.name,
                    qty: qty,
                    price: p.price,
                    tax_rate: p.tax_rate,
                    sku: p.sku,
                    stock_qty: p.stock_qty
                });
            });
        });
    }

    function loadCatalog() {
        if (kind === "quick") {
            els.grid.hidden = true;
            els.quick.hidden = false;
            return;
        }
        els.quick.hidden = true;
        els.grid.hidden = false;
        els.grid.innerHTML = '<div class="pos-empty">Loading…</div>';
        const params = new URLSearchParams({
            kind: kind,
            category: kind === "product" ? category : "",
            q: els.search.value.trim()
        });
        fetch("/pos/catalog?" + params.toString())
            .then(function (res) { return res.json(); })
            .then(function (rows) {
                if (!rows.length) {
                    els.grid.innerHTML = '<div class="pos-empty">No items found.</div>';
                    return;
                }
                els.grid.innerHTML = rows.map(cardHtml).join("");
                bindCards(rows);
            })
            .catch(function () {
                els.grid.innerHTML = '<div class="pos-empty">Could not load catalog.</div>';
            });
    }

    function addToCart(item) {
        const key = lineKey(item);
        const found = cart.find(function (line) { return lineKey(line) === key; });
        if (found) {
            const next = found.qty + item.qty;
            if (item.item_type === "product" && item.stock_qty != null && next > item.stock_qty) {
                Swal.fire({ icon: "warning", title: "Not enough stock" });
                return;
            }
            found.qty = next;
        } else {
            cart.push(item);
        }
        renderCart();
    }

    function renderCart() {
        const t = totals();
        const n = cart.reduce(function (s, l) { return s + l.qty; }, 0);
        els.count.textContent = n + (n === 1 ? " item" : " items");
        if (!cart.length) {
            els.lines.innerHTML = '<div class="pos-empty">Cart is empty.</div>';
        } else {
            els.lines.innerHTML = cart.map(function (line, idx) {
                return (
                    '<div class="pos-line">' +
                    '<div class="pos-line-top"><span>' + escapeHtml(line.name) + "</span><span>" + money(line.qty * line.price) + "</span></div>" +
                    '<div class="pos-line-meta">' + money(line.price) + " each" + (line.sku ? " · " + escapeHtml(line.sku) : "") + "</div>" +
                    '<div class="pos-line-actions">' +
                    '<div class="pos-stepper"><button type="button" data-line="' + idx + '" data-act="minus">-</button><span>' + line.qty + '</span><button type="button" data-line="' + idx + '" data-act="plus">+</button></div>' +
                    '<button type="button" class="pos-line-remove" data-line="' + idx + '" data-act="remove"><i class="bi bi-trash"></i></button>' +
                    "</div></div>"
                );
            }).join("");
        }
        els.subtotal.textContent = money(t.subtotal);
        els.tax.textContent = money(t.gst);
        els.grand.textContent = money(t.grand);
        renderDay();
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    els.lines.addEventListener("click", function (e) {
        const btn = e.target.closest("[data-act]");
        if (!btn) return;
        const idx = parseInt(btn.getAttribute("data-line"), 10);
        const line = cart[idx];
        if (!line) return;
        const act = btn.getAttribute("data-act");
        if (act === "remove") cart.splice(idx, 1);
        if (act === "minus") line.qty = Math.max(1, line.qty - 1);
        if (act === "plus") {
            if (line.item_type === "product" && line.stock_qty != null && line.qty + 1 > line.stock_qty) {
                Swal.fire({ icon: "warning", title: "Not enough stock" });
                return;
            }
            line.qty += 1;
        }
        renderCart();
    });

    document.querySelectorAll(".pos-mode").forEach(function (btn) {
        btn.addEventListener("click", function () {
            document.querySelectorAll(".pos-mode").forEach(function (b) { b.classList.remove("is-on"); });
            btn.classList.add("is-on");
            kind = btn.getAttribute("data-kind");
            loadCatalog();
        });
    });

    let searchTimer = null;
    els.search.addEventListener("input", function () {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(loadCatalog, 200);
    });

    els.discount.addEventListener("input", renderCart);

    document.getElementById("posClear").addEventListener("click", function () {
        if (!cart.length) return;
        Swal.fire({
            icon: "warning",
            title: "Clear cart?",
            showCancelButton: true,
            confirmButtonText: "Clear"
        }).then(function (r) {
            if (r.isConfirmed) {
                cart = [];
                renderCart();
            }
        });
    });

    document.querySelectorAll(".pos-pay").forEach(function (btn) {
        btn.addEventListener("click", function () {
            document.querySelectorAll(".pos-pay").forEach(function (b) { b.classList.remove("is-on"); });
            btn.classList.add("is-on");
            payMode = btn.getAttribute("data-mode");
            document.getElementById("posSplit").classList.remove("is-on");
            els.splitBox.hidden = true;
        });
    });

    document.getElementById("posSplit").addEventListener("click", function () {
        payMode = "split";
        document.querySelectorAll(".pos-pay").forEach(function (b) { b.classList.remove("is-on"); });
        this.classList.add("is-on");
        els.splitBox.hidden = false;
        const t = totals();
        els.splitCash.value = t.grand.toFixed(2);
        els.splitUpi.value = "0.00";
    });

    els.dayBtn.addEventListener("click", function () {
        if (dayOpen()) return;
        fetch("/pos/session/start", { method: "POST", headers: headers(), body: "{}" })
            .then(function (res) { return res.json(); })
            .then(function (body) {
                if (!body.ok) {
                    Swal.fire({ icon: "error", title: body.error || "Could not start the day" });
                    return;
                }
                daySession = body.session;
                renderDay();
            });
    });

    document.getElementById("quickAdd").addEventListener("click", function () {
        const name = document.getElementById("quickName").value.trim();
        const price = Number(document.getElementById("quickPrice").value || 0);
        const qty = Number(document.getElementById("quickQty").value || 0);
        if (!name || price < 0 || qty <= 0) {
            Swal.fire({ icon: "warning", title: "Enter item name, price and quantity." });
            return;
        }
        addToCart({ product_id: null, item_type: "quick", name: name, qty: qty, price: price, tax_rate: 0 });
        document.getElementById("quickName").value = "";
    });

    document.getElementById("posAddCustomer").addEventListener("click", function () {
        const modal = document.getElementById("quickCustomerModal");
        document.getElementById("quick_customer_name").value = document.getElementById("customer_search").value.trim();
        document.getElementById("quick_customer_phone").value = "";
        if (window.bootstrap) window.bootstrap.Modal.getOrCreateInstance(modal).show();
    });

    document.getElementById("quick_customer_phone").addEventListener("input", function () {
        this.value = this.value.replace(/\D/g, "").substring(0, 10);
    });

    document.getElementById("quickCustomerSave").addEventListener("click", function () {
        const name = document.getElementById("quick_customer_name").value.trim();
        const phone = document.getElementById("quick_customer_phone").value.replace(/\D/g, "");
        if (!name || phone.length !== 10) {
            Swal.fire({ icon: "warning", title: "Enter name and a 10-digit mobile number." });
            return;
        }
        fetch("/sales/quick-customer", {
            method: "POST",
            headers: headers(),
            body: JSON.stringify({ name: name, phone: phone, csrf_token: csrf })
        })
            .then(function (res) { return res.json(); })
            .then(function (body) {
                if (!body.ok) {
                    Swal.fire({ icon: "error", title: body.error || "Could not save customer" });
                    return;
                }
                document.getElementById("customer_id").value = body.id;
                document.getElementById("customer_search").value = body.name + " (" + body.phone + ")";
                if (window.bootstrap) {
                    window.bootstrap.Modal.getOrCreateInstance(document.getElementById("quickCustomerModal")).hide();
                }
            })
            .catch(function () {
                Swal.fire({ icon: "error", title: "Could not save customer" });
            });
    });

    (function initCustomerSearch() {
        const search = document.getElementById("customer_search");
        const hidden = document.getElementById("customer_id");
        const results = document.getElementById("customer_results");
        let timer = null;
        function hide() {
            results.hidden = true;
            results.innerHTML = "";
        }
        search.addEventListener("input", function () {
            hidden.value = "";
            const q = search.value.trim();
            clearTimeout(timer);
            if (!q) {
                hide();
                return;
            }
            timer = setTimeout(function () {
                fetch("/sales/customer-search?q=" + encodeURIComponent(q))
                    .then(function (res) { return res.json(); })
                    .then(function (rows) {
                        results.innerHTML = "";
                        (rows || []).forEach(function (row) {
                            const btn = document.createElement("button");
                            btn.type = "button";
                            btn.className = "customer-suggest-item";
                            btn.innerHTML = "<span>" + escapeHtml(row.name) + "</span><small>" + escapeHtml(row.phone || "") + "</small>";
                            btn.addEventListener("mousedown", function (e) {
                                e.preventDefault();
                                hidden.value = row.id;
                                search.value = row.name + (row.phone ? " (" + row.phone + ")" : "");
                                hide();
                            });
                            results.appendChild(btn);
                        });
                        results.hidden = false;
                    });
            }, 200);
        });
        search.addEventListener("blur", function () { setTimeout(hide, 150); });
    })();

    els.complete.addEventListener("click", function () {
        if (!dayOpen()) {
            Swal.fire({ icon: "warning", title: "Start the business day first." });
            return;
        }
        if (!cart.length) {
            Swal.fire({ icon: "warning", title: "Cart is empty." });
            return;
        }
        const t = totals();
        let payments = [];
        if (payMode === "split") {
            payments = [
                { mode: "cash", amount: Number(els.splitCash.value || 0) },
                { mode: "upi", amount: Number(els.splitUpi.value || 0) }
            ];
        }
        const payload = {
            items: cart.map(function (line) {
                return {
                    product_id: line.product_id,
                    item_type: line.item_type,
                    name: line.name,
                    qty: line.qty,
                    price: line.price,
                    tax_rate: line.tax_rate
                };
            }),
            discount_amount: t.discount,
            customer_id: document.getElementById("customer_id").value || null,
            payment_mode: payMode,
            payments: payments,
            csrf_token: csrf
        };
        els.complete.disabled = true;
        fetch("/pos/complete", { method: "POST", headers: headers(), body: JSON.stringify(payload) })
            .then(function (res) { return res.json().then(function (body) { return { ok: res.ok, body: body }; }); })
            .then(function (result) {
                els.complete.disabled = false;
                if (!result.body.ok) {
                    Swal.fire({ icon: "error", title: result.body.error || "Could not complete sale" });
                    return;
                }
                Swal.fire({
                    icon: "success",
                    title: "Sale complete",
                    text: "Bill " + result.body.bill_no + " · " + money(result.body.grand_total)
                });
                cart = [];
                els.discount.value = "0";
                renderCart();
                loadCatalog();
            })
            .catch(function () {
                els.complete.disabled = false;
                Swal.fire({ icon: "error", title: "Could not complete sale" });
            });
    });

    renderCats(categories);
    renderDay();
    renderCart();
    loadCatalog();
})();
