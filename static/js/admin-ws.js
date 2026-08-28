/**
 * Connexion WebSocket STOMP vers le backend Spring Boot.
 *
 * IMPORTANT — production :
 * L'URL WebSocket est ouverte PAR LE NAVIGATEUR, pas par Django.
 * PUBLIC_BACKEND_HOST doit donc être le domaine PUBLIC (ex. ndbshopping.duckdns.org),
 * jamais le nom du conteneur Docker (`backend`) ni une IP interne.
 * En HTTPS, le navigateur exige WSS (pas de contenu mixte). Nginx doit proxifier /ws.
 *
 * Le backend autorise /ws sans JWT (permitAll) et pousse sur /topic/admin-notifications.
 */
(function () {
  const host = window.NDB_PUBLIC_BACKEND_HOST;
  if (!host || typeof StompJs === "undefined") {
    return;
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const brokerURL = `${protocol}://${host}/ws`;

  const client = new StompJs.Client({
    brokerURL: brokerURL,
    reconnectDelay: 5000,
    heartbeatIncoming: 10000,
    heartbeatOutgoing: 10000,
  });

  function bumpBadges(selector) {
    document.querySelectorAll(selector).forEach(function (badge) {
      const current = parseInt(badge.textContent, 10);
      const next = (Number.isNaN(current) ? 0 : current) + 1;
      badge.textContent = String(next);
      badge.classList.remove("d-none");
    });
  }

  function bumpBadge(id) {
    bumpBadges("#" + id);
  }

  function toastMeta(notif) {
    const type = (notif && notif.type) || "";
    const i18n = window.NDB_I18N || {};
    if (type === "PRODUIT_A_VALIDER") {
      return {
        cls: "toast align-items-center text-bg-info border-0",
        label: i18n.productToValidate || "Produit à valider",
        icon: "bi-box-seam",
      };
    }
    if (type === "NOUVELLE_COMMANDE") {
      return {
        cls: "toast align-items-center text-bg-warning border-0",
        label: i18n.newOrder || "Nouvelle commande",
        icon: "bi-receipt",
      };
    }
    return {
      cls: "toast align-items-center text-bg-warning border-0",
      label: i18n.newNotification || "Nouvelle notification",
      icon: "bi-bell",
    };
  }

  function showToast(notif) {
    const container = document.getElementById("adminToastContainer");
    if (!container || typeof bootstrap === "undefined") return;
    const meta = toastMeta(notif);
    const message = (notif && notif.message) || meta.label;
    const el = document.createElement("div");
    el.className = meta.cls;
    el.setAttribute("role", "alert");
    el.innerHTML = `<div class="d-flex"><div class="toast-body"><i class="bi ${meta.icon} me-1"></i><strong>${meta.label}</strong> — ${message}</div>
      <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
    container.appendChild(el);
    const t = new bootstrap.Toast(el, { delay: 8000 });
    t.show();
    el.addEventListener("hidden.bs.toast", () => el.remove());
  }

  client.onConnect = function () {
    client.subscribe("/topic/admin-notifications", function (message) {
      let notif = {};
      try {
        notif = JSON.parse(message.body);
      } catch (e) {
        notif = { message: message.body };
      }
      bumpBadge("adminNotifBadge");
      if (notif.type === "PRODUIT_A_VALIDER") {
        bumpBadges(".admin-pending-products-badge");
      }
      showToast(notif);
    });
  };

  client.onStompError = function () {
    /* reconnexion automatique via reconnectDelay */
  };

  client.activate();
})();
