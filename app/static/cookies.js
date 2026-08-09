/* Cookie consent banner.
 *
 * Strictly-necessary cookies (age gate, session, feed key, this choice) always
 * run — they're required for the site to work and are disclosed in the Cookie
 * Policy. This banner governs ONLY optional analytics, which stay off until the
 * visitor explicitly accepts. The choice is stored in localStorage so the
 * banner doesn't reappear every page.
 */
(function () {
  "use strict";

  var KEY = "amorae_cookie_choice"; // "accept" | "decline"
  var banner = document.getElementById("cookie-banner");
  if (!banner) return;

  var choice = null;
  try {
    choice = localStorage.getItem(KEY);
  } catch (e) {
    // Private mode / storage blocked — treat as no choice yet.
  }

  if (!choice) {
    banner.hidden = false;
  } else if (choice === "accept") {
    enableAnalytics();
  }

  banner.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-cookie]");
    if (!btn) return;
    var value = btn.getAttribute("data-cookie");
    try {
      localStorage.setItem(KEY, value);
    } catch (e) {
      /* ignore */
    }
    banner.hidden = true;
    if (value === "accept") enableAnalytics();
  });

  function enableAnalytics() {
    // Placeholder — a privacy-respecting analytics tag would initialise here,
    // and only here, so it never loads without consent. Nothing to load yet.
    window.__amoraeAnalytics = { enabled: true };
  }

  // Let a policy page re-open the banner ("manage cookies").
  window.amoraeManageCookies = function () {
    banner.hidden = false;
  };
})();
