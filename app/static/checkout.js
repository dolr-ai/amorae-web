/* Checkout — keeps the billing-terms panel in sync with the selected plan and
 * gates the submit button on explicit recurring-billing consent.
 *
 * No card data is ever handled here. The button leads to the processor's
 * hosted form; collecting card details in our own page is prohibited.
 */
(function () {
  "use strict";

  var form = document.getElementById("checkout-form");
  if (!form) return;

  var total = document.getElementById("bt-total");
  var permonth = document.getElementById("bt-permonth");
  var rebill = document.getElementById("bt-rebill");
  var consent = document.getElementById("consent");
  var submit = document.getElementById("checkout-submit");

  function selectedPlan() {
    return form.querySelector('input[name="tier"]:checked');
  }

  function syncTerms() {
    var plan = selectedPlan();
    if (!plan) return;
    var t = plan.dataset.total;
    var pm = plan.dataset.permonth;
    var months = Number(plan.dataset.months) || 1;
    total.textContent = "$" + t;
    permonth.textContent = "$" + pm + "/mo";
    rebill.textContent =
      months === 1
        ? "$" + t + " every month"
        : "$" + t + " every " + months + " months";

    // Reflect selection styling on the plan rows.
    form.querySelectorAll(".plan").forEach(function (row) {
      row.classList.toggle("is-selected", row.contains(plan));
    });
  }

  function syncSubmit() {
    submit.disabled = !consent.checked;
  }

  form.addEventListener("change", function (e) {
    if (e.target.name === "tier") syncTerms();
    if (e.target === consent) syncSubmit();
    if (e.target.name === "rail") {
      form.querySelectorAll(".rail-opt").forEach(function (row) {
        row.classList.toggle("is-selected", row.contains(e.target) && e.target.checked);
      });
    }
  });

  syncTerms();
  syncSubmit();
})();
