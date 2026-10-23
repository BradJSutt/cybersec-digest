(function () {
    "use strict";

    var nav = document.getElementById("siteNav");
    var toggle = document.getElementById("navToggle");
    var links = document.getElementById("navLinks");

    if (nav) {
        var setScrolled = function () {
            nav.classList.toggle("is-scrolled", window.scrollY > 8);
        };
        setScrolled();
        window.addEventListener("scroll", setScrolled, { passive: true });
    }

    if (!toggle || !links) {
        return;
    }

    var closeMenu = function () {
        links.classList.remove("is-open");
        toggle.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "Toggle navigation");
    };

    toggle.addEventListener("click", function () {
        var open = links.classList.toggle("is-open");
        toggle.classList.toggle("is-open", open);
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        toggle.setAttribute("aria-label", open ? "Close navigation" : "Toggle navigation");
    });

    links.addEventListener("click", function (event) {
        if (event.target.closest("a")) {
            closeMenu();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeMenu();
        }
    });

    document.addEventListener("click", function (event) {
        if (!links.classList.contains("is-open")) {
            return;
        }
        if (!links.contains(event.target) && !toggle.contains(event.target)) {
            closeMenu();
        }
    });
})();
