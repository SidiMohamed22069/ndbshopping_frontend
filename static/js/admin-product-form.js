/**
 * Formulaire produit admin : charge les attributs dynamiques
 * via le proxy Django GET /api/categories/{id}/attributes/ (relais vers Spring Boot)
 * quand la catégorie change, sans recharger la page.
 */
(function () {
  const select = document.getElementById("categoryId");
  const container = document.getElementById("dynamicAttributes");
  if (!select || !container) return;

  const endpointTemplate = container.dataset.endpoint || "";

  const i18n = {
    loading: container.dataset.msgLoading || "Chargement des attributs…",
    choose: container.dataset.msgChoose || "Choisissez une catégorie pour afficher les champs spécifiques (hôtel, voiture, etc.).",
    fail: container.dataset.msgFail || "Impossible de charger les attributs.",
    none: container.dataset.msgNone || "Aucun attribut spécifique pour cette catégorie.",
    down: container.dataset.msgDown || "Service temporairement indisponible.",
    yes: container.dataset.msgYes || "Oui",
    no: container.dataset.msgNo || "Non",
  };

  function inputFor(attr, currentValues) {
    const name = `attr_${attr.id}`;
    const current = currentValues[attr.id] || currentValues[String(attr.id)] || "";
    const type = attr.typeValeur;
    const label = attr.nomAttribut || "Attribut";
    let field = "";
    if (type === "BOOLEEN") {
      field = `<select class="form-select" name="${name}">
        <option value="false"${current === "false" || current === false ? " selected" : ""}>${i18n.no}</option>
        <option value="true"${current === "true" || current === true ? " selected" : ""}>${i18n.yes}</option>
      </select>`;
    } else if (type === "NOMBRE") {
      field = `<input class="form-control" type="number" step="any" name="${name}" value="${current}">`;
    } else if (type === "DATE") {
      field = `<input class="form-control" type="date" name="${name}" value="${current}">`;
    } else {
      field = `<input class="form-control" type="text" name="${name}" value="${current}">`;
    }
    return `<div class="mb-3"><label class="form-label">${label}</label>${field}</div>`;
  }

  async function loadAttributes(categoryId) {
    container.innerHTML = `<p class="text-muted small">${i18n.loading}</p>`;
    if (!categoryId) {
      container.innerHTML = `<p class="text-muted small">${i18n.choose}</p>`;
      return;
    }
    const url = endpointTemplate.replace("999999", categoryId);
    try {
      const response = await fetch(url, { headers: { Accept: "application/json" } });
      if (!response.ok) {
        container.innerHTML = `<p class="text-danger small">${i18n.fail}</p>`;
        return;
      }
      const attrs = await response.json();
      const current = {};
      (window.NDB_PRODUCT_ATTRS || []).forEach(function (a) {
        current[a.attributeDefinitionId] = a.valeur;
      });
      if (!attrs || !attrs.length) {
        container.innerHTML = `<p class="text-muted small">${i18n.none}</p>`;
        return;
      }
      container.innerHTML = attrs.map(function (attr) {
        return inputFor(attr, current);
      }).join("");
    } catch (e) {
      container.innerHTML = `<p class="text-danger small">${i18n.down}</p>`;
    }
  }

  select.addEventListener("change", function () {
    loadAttributes(select.value);
  });

  if (select.value) {
    loadAttributes(select.value);
  }
})();
