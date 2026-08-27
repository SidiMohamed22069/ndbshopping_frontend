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

  function bumpBadge() {
    const badge = document.getElementById("adminNotifBadge");
    if (!badge) return;
    const current = parseInt(badge.textContent, 10);
    const next = (Number.isNaN(current) ? 0 : current) + 1;
    badge.textContent = String(next);
    badge.classList.remove("d-none");
  }

  function showToast(notif) {
    const container = document.getElementById("adminToastContainer");
    if (!container || typeof bootstrap === "undefined") return;
    const message = (notif && notif.message) || "Nouvelle notification";
    const el = document.createElement("div");
    el.className = "toast align-items-center text-bg-warning border-0";
    el.setAttribute("role", "alert");
    el.innerHTML = `<div class="d-flex"><div class="toast-body"><strong>NDB</strong> — ${message}</div>
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
      bumpBadge();
      showToast(notif);
    });
  };

  client.onStompError = function () {
    /* reconnexion automatique via reconnectDelay */
  };

  client.activate();
})();
