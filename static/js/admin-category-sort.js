/**
 * Réordonnancement des catégories admin via SortableJS + proxy Django.
 */
(function () {
  const list = document.getElementById("categorySortList");
  if (!list || typeof Sortable === "undefined") return;

  const csrfInput = list.querySelector("[name=csrfmiddlewaretoken]");
  const reorderUrl = list.dataset.reorderUrl || "";
  let snapshot = [];
  let busy = false;

  function idsFromList() {
    return Array.from(list.querySelectorAll(":scope > .category-sort-item[data-category-id]")).map(
      function (item) {
        return item.getAttribute("data-category-id");
      }
    );
  }

  function restore() {
    snapshot.forEach(function (node) {
      list.appendChild(node);
    });
  }

  function showToast(message, variant) {
    const container = document.getElementById("adminToastContainer");
    if (!container || typeof bootstrap === "undefined") return;
    const el = document.createElement("div");
    el.className =
      "toast align-items-center border-0 " +
      (variant === "danger" ? "text-bg-danger" : "text-bg-success");
    el.setAttribute("role", "status");
    el.innerHTML =
      '<div class="d-flex"><div class="toast-body">' +
      message +
      '</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>';
    container.appendChild(el);
    const toast = new bootstrap.Toast(el, { delay: 3500 });
    toast.show();
    el.addEventListener("hidden.bs.toast", function () {
      el.remove();
    });
  }

  new Sortable(list, {
    handle: ".category-sort-handle",
    animation: 150,
    ghostClass: "category-sort-ghost",
    chosenClass: "category-sort-chosen",
    dragClass: "category-sort-drag",
    onStart: function () {
      snapshot = Array.from(list.children);
    },
    onEnd: function (event) {
      if (event.oldIndex === event.newIndex) return;
      if (busy) {
        restore();
        return;
      }
      const ordreIds = idsFromList();
      if (!ordreIds.length || !reorderUrl) return;
      busy = true;
      fetch(reorderUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": (csrfInput && csrfInput.value) || "",
        },
        body: JSON.stringify({ ordreIds: ordreIds }),
      })
        .then(function (response) {
          return response.json().catch(function () {
            return {};
          }).then(function (data) {
            if (!response.ok || data.ok === false) {
              throw new Error(data.error || list.dataset.msgFail);
            }
            showToast(list.dataset.msgOk || "Ordre enregistré", "success");
          });
        })
        .catch(function (err) {
          restore();
          showToast(err.message || list.dataset.msgFail || "Impossible d'enregistrer l'ordre.", "danger");
        })
        .finally(function () {
          busy = false;
        });
    },
  });
})();
