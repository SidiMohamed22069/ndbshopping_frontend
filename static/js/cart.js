/**
 * Ajout au panier en AJAX (fetch) pour éviter un rechargement complet.
 * Les formulaires .js-add-to-cart restent fonctionnels sans JS (POST classique).
 */
(function () {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop().split(";").shift();
    }
    return "";
  }

  function toast(message, ok) {
    const container = document.getElementById("toastContainer");
    if (!container) return;
    const el = document.createElement("div");
    el.className = `toast align-items-center text-bg-${ok ? "success" : "danger"} border-0`;
    el.setAttribute("role", "alert");
    el.innerHTML = `<div class="d-flex"><div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
    container.appendChild(el);
    const t = new bootstrap.Toast(el, { delay: 2500 });
    t.show();
    el.addEventListener("hidden.bs.toast", () => el.remove());
  }

  document.addEventListener("submit", async function (event) {
    const form = event.target;
    if (!form.classList.contains("js-add-to-cart")) return;
    event.preventDefault();
    const data = new FormData(form);
    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: {
          "X-CSRFToken": data.get("csrfmiddlewaretoken") || getCookie("csrftoken"),
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
        },
        body: data,
      });
      const payload = await response.json();
      if (payload.ok) {
        const badge = document.getElementById("cartBadge");
        if (badge) badge.textContent = payload.cart_count;
        toast(payload.message || (window.NDB_I18N && window.NDB_I18N.addedToCart) || "Ajouté au panier", true);
      } else {
        toast(payload.error || (window.NDB_I18N && window.NDB_I18N.cannotAddToCart) || "Impossible d'ajouter au panier", false);
      }
    } catch (err) {
      toast((window.NDB_I18N && window.NDB_I18N.unavailable) || "Service temporairement indisponible", false);
    }
  });
})();
