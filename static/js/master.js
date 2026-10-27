/* BusinessOS master script - shared by every page */
(function () {
    "use strict";

    /* ---- Sidebar drawer (hamburger) ---- */
    function initSidebar() {
        var sidebar = document.getElementById("sidebar");
        var overlay = document.getElementById("sidebarOverlay");
        var openBtn = document.getElementById("openSidebar");
        var closeBtn = document.getElementById("closeSidebar");
        if (!sidebar) return;

        function open() {
            sidebar.classList.add("open");
            if (overlay) overlay.classList.add("visible");
            if (openBtn) openBtn.setAttribute("aria-expanded", "true");
            document.body.classList.add("no-scroll");
        }
        function close() {
            sidebar.classList.remove("open");
            if (overlay) overlay.classList.remove("visible");
            if (openBtn) openBtn.setAttribute("aria-expanded", "false");
            document.body.classList.remove("no-scroll");
        }
        if (openBtn) openBtn.addEventListener("click", open);
        if (closeBtn) closeBtn.addEventListener("click", close);
        if (overlay) overlay.addEventListener("click", close);
        sidebar.querySelectorAll("a").forEach(function (a) {
            a.addEventListener("click", function () { if (window.innerWidth <= 960) close(); });
        });
        document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
        window.addEventListener("resize", function () { if (window.innerWidth > 960) close(); });
    }

    /* ---- Public landing menu ---- */
    function initPublicNav() {
        var btn = document.getElementById("pubToggle");
        var links = document.getElementById("pubLinks");
        if (!btn || !links) return;
        btn.addEventListener("click", function () {
            var open = links.classList.toggle("open");
            btn.setAttribute("aria-expanded", open ? "true" : "false");
        });
        links.querySelectorAll("a").forEach(function (a) {
            a.addEventListener("click", function () { links.classList.remove("open"); });
        });
    }

    /* ---- Toasts auto-dismiss ---- */
    function initToasts() {
        document.querySelectorAll(".toast").forEach(function (t) {
            var remove = function () { t.remove(); };
            var btn = t.querySelector("button");
            if (btn) btn.addEventListener("click", remove);
            if (t.classList.contains("alert-success") || t.classList.contains("alert-info")) setTimeout(remove, 5000);
        });
    }

    /* ---- Confirm dialogs: <form data-confirm="Are you sure?"> ---- */
    function initConfirm() {
        document.addEventListener("submit", function (e) {
            var msg = e.target.getAttribute && e.target.getAttribute("data-confirm");
            if (msg && !window.confirm(msg)) e.preventDefault();
        });
    }

    /* ---- Auto-submit filters: <select data-autosubmit> ---- */
    function initAutoSubmit() {
        document.querySelectorAll("[data-autosubmit]").forEach(function (el) {
            el.addEventListener("change", function () { el.form && el.form.submit(); });
        });
    }

    /* ---- Password show/hide ---- */
    function initPasswordToggle() {
        document.querySelectorAll(".toggle-pass").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var input = btn.parentElement.querySelector("input");
                if (!input) return;
                var show = input.type === "password";
                input.type = show ? "text" : "password";
                btn.setAttribute("aria-pressed", show ? "true" : "false");
                btn.textContent = show ? "Hide" : "Show";
            });
        });
    }

    /* ---- Prevent double submits ---- */
    function initSingleSubmit() {
        document.addEventListener("submit", function (e) {
            if (e.defaultPrevented) return;
            var btn = e.target.querySelector && e.target.querySelector("button[type=submit]:not([data-multi])");
            if (btn) setTimeout(function () { btn.disabled = true; }, 0);
        });
    }

    /* ---- Live date label ---- */
    function initDate() {
        var d = document.getElementById("currentDate");
        if (!d) return;
        var now = new Date();
        d.textContent = now.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
        var day = document.getElementById("currentDay");
        if (day) day.textContent = now.toLocaleDateString(undefined, { weekday: "long" }).toUpperCase();
    }

    function init() {
        initSidebar(); initPublicNav(); initToasts(); initConfirm();
        initAutoSubmit(); initPasswordToggle(); initSingleSubmit(); initDate();
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
})();
