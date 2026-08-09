/* Cookie consent banner.
 *
 * Strictly-necessary cookies (age gate, session, feed key, this choice) always
 * run — they're required for the site to work and are disclosed in the Cookie
 * Policy. This banner governs ONLY optional analytics, which stay off until the
 * visitor explicitly accepts.
 *
 * The choice is stored in a first-party COOKIE, not localStorage. localStorage
 * fails silently on iOS Safari private mode, "block cross-site tracking", and
 * many in-app webviews — so a localStorage-only banner reappears every page and
 * reads as "the Accept button doesn't work". Cookies persist across navigation
 * in those environments (the site already relies on the age-gate cookie), so
 * the choice actually sticks.
 */
(function () {
  "use strict";

  var NAME = "amorae_cookie_choice"; // "accept" | "decline"
  var banner = document.getElementById("cookie-banner");
  if (!banner) return;

  function readChoice() {
    var m = document.cookie.match(/(?:^|;\s*)amorae_cookie_choice=(accept|decline)/);
    return m ? m[1] : null;
  }

  function saveChoice(value) {
    var oneYear = 365 * 24 * 60 * 60;
    var secure = location.protocol === "https:" ? "; Secure" : "";
    document.cookie =
      NAME + "=" + value + "; Max-Age=" + oneYear + "; Path=/; SameSite=Lax" + secure;
    // Best-effort mirror to localStorage; harmless if it throws.
    try {
      localStorage.setItem(NAME, value);
    } catch (e) {
      /* ignore */
    }
  }

  var choice = readChoice();
  if (!choice) {
    banner.hidden = false;
  } else if (choice === "accept") {
    enableAnalytics();
  }

  banner.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-cookie]");
    if (!btn) return;
    var value = btn.getAttribute("data-cookie");
    saveChoice(value);
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
