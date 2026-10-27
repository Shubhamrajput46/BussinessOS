/* Order form: tick products, set quantities, see live totals. */
(function () {
    "use strict";
    var form = document.getElementById("orderForm");
    if (!form) return;
    var rows = form.querySelectorAll(".pick-row");
    var money = function (n) { return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); };

    function recalc() {
        var subtotal = 0;
        rows.forEach(function (row) {
            var box = row.querySelector("input[type=checkbox]"), qty = row.querySelector(".qty");
            row.classList.toggle("selected", box.checked);
            qty.disabled = !box.checked;
            if (box.checked) {
                var q = parseInt(qty.value, 10) || 0;
                subtotal += q * parseFloat(row.dataset.price || "0");
            }
        });
        var discount = parseFloat(form.elements.discount.value) || 0;
        var tax = parseFloat(form.elements.tax.value) || 0;
        document.getElementById("sumSubtotal").textContent = money(subtotal);
        document.getElementById("sumTotal").textContent = money(Math.max(subtotal - discount + tax, 0));
    }
    form.addEventListener("input", recalc);
    form.addEventListener("change", recalc);

    var search = document.getElementById("pickSearch");
    if (search) search.addEventListener("input", function () {
        var q = search.value.toLowerCase();
        rows.forEach(function (row) { row.classList.toggle("hidden", q && row.dataset.name.indexOf(q) === -1); });
    });
    recalc();
})();
