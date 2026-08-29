/**
 * Galerie + vidéos produit : ajouts / suppressions via les proxies Django.
 */
(function () {
  const root = document.getElementById("productMediaForm");
  if (!root) return;

  const csrfInput = root.querySelector("[name=csrfmiddlewaretoken]");
  const alertBox = document.getElementById("productMediaAlert");
  const imagesEl = document.getElementById("productMediaImages");
  const videosEl = document.getElementById("productMediaVideos");
  const imageInput = document.getElementById("productMediaImageInput");
  const videoInput = document.getElementById("productMediaVideoInput");
  const addImageBtn = document.getElementById("productMediaAddImage");
  const addVideoBtn = document.getElementById("productMediaAddVideo");
  const imageHint = document.getElementById("productMediaImageHint");
  const videoHint = document.getElementById("productMediaVideoHint");

  const maxImages = Number(root.dataset.maxImages || 6);
  const maxVideos = Number(root.dataset.maxVideos || 2);
  const maxImageBytes = Number(root.dataset.maxImageBytes || 5 * 1024 * 1024);
  const maxVideoBytes = Number(root.dataset.maxVideoBytes || 20 * 1024 * 1024);

  const images = [];
  const videos = [];
  const initialEl = document.getElementById("productMediaInitial");
  if (initialEl) {
    try {
      const data = JSON.parse(initialEl.textContent || "{}");
      (data.images || []).forEach(function (item) {
        if (item && item.id) images.push(item);
      });
      (data.videos || []).forEach(function (item) {
        if (item && item.id) videos.push(item);
      });
    } catch (err) {
      /* ignore JSON invalide */
    }
  }

  function csrfHeaders() {
    const token = (csrfInput && csrfInput.value) || "";
    return token ? { "X-CSRFToken": token } : {};
  }

  function showError(message) {
    if (!alertBox) return;
    if (!message) {
      alertBox.hidden = true;
      alertBox.textContent = "";
      return;
    }
    alertBox.hidden = false;
    alertBox.textContent = message;
  }

  function withId(url, id) {
    return String(url || "").replace("/0/supprimer/", "/" + id + "/supprimer/");
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function updateButtons() {
    const imageFull = images.length >= maxImages;
    const videoFull = videos.length >= maxVideos;
    if (addImageBtn) {
      addImageBtn.disabled = imageFull;
      addImageBtn.setAttribute("aria-disabled", imageFull ? "true" : "false");
    }
    if (addVideoBtn) {
      addVideoBtn.disabled = videoFull;
      addVideoBtn.setAttribute("aria-disabled", videoFull ? "true" : "false");
    }
    if (imageHint) {
      imageHint.textContent = imageFull
        ? root.dataset.msgImgLimit
        : imageHint.dataset.defaultHint || imageHint.textContent;
    }
    if (videoHint) {
      videoHint.textContent = videoFull
        ? root.dataset.msgVidLimit
        : videoHint.dataset.defaultHint || videoHint.textContent;
    }
  }

  function render() {
    if (imageHint && !imageHint.dataset.defaultHint) {
      imageHint.dataset.defaultHint = imageHint.textContent;
    }
    if (videoHint && !videoHint.dataset.defaultHint) {
      videoHint.dataset.defaultHint = videoHint.textContent;
    }
    const deleteLabel = root.dataset.msgDelete || "Supprimer";
    if (imagesEl) {
      imagesEl.innerHTML = images
        .map(function (item) {
          return (
            '<div class="product-media-item">' +
            '<img src="' + escapeHtml(item.url) + '" alt="">' +
            '<button type="button" class="btn btn-sm btn-outline-danger" data-delete-image="' +
            escapeHtml(item.id) +
            '">' +
            escapeHtml(deleteLabel) +
            "</button>" +
            "</div>"
          );
        })
        .join("");
    }
    if (videosEl) {
      videosEl.innerHTML = videos
        .map(function (item) {
          return (
            '<div class="product-media-video-item">' +
            '<video class="product-video" controls preload="metadata" src="' +
            escapeHtml(item.url) +
            '"></video>' +
            '<button type="button" class="btn btn-sm btn-outline-danger" data-delete-video="' +
            escapeHtml(item.id) +
            '">' +
            escapeHtml(deleteLabel) +
            "</button>" +
            "</div>"
          );
        })
        .join("");
    }
    updateButtons();
  }

  function setBusy(busy) {
    root.setAttribute("aria-busy", busy ? "true" : "false");
    if (addImageBtn) addImageBtn.disabled = busy || images.length >= maxImages;
    if (addVideoBtn) addVideoBtn.disabled = busy || videos.length >= maxVideos;
  }

  function validateImage(file) {
    if (images.length >= maxImages) return root.dataset.msgImgLimit;
    if (file.size > maxImageBytes) return root.dataset.msgImgHeavy;
    const type = (file.type || "").toLowerCase();
    const name = (file.name || "").toLowerCase();
    if (
      ["image/jpeg", "image/jpg", "image/png", "image/webp"].indexOf(type) === -1 &&
      !/\.(jpe?g|png|webp)$/.test(name)
    ) {
      return root.dataset.msgImgFmt;
    }
    return "";
  }

  function validateVideo(file) {
    if (videos.length >= maxVideos) return root.dataset.msgVidLimit;
    if (file.size > maxVideoBytes) return root.dataset.msgVidHeavy;
    const type = (file.type || "").toLowerCase();
    const name = (file.name || "").toLowerCase();
    if (["video/mp4", "video/webm"].indexOf(type) === -1 && !/\.(mp4|webm)$/.test(name)) {
      return root.dataset.msgVidFmt;
    }
    return "";
  }

  async function postFile(url, field, file) {
    const body = new FormData();
    body.append(field, file);
    const response = await fetch(url, {
      method: "POST",
      headers: csrfHeaders(),
      body: body,
      credentials: "same-origin",
    });
    let data = {};
    try {
      data = await response.json();
    } catch (err) {
      data = {};
    }
    if (!response.ok || !data.ok) {
      throw new Error(data.error || root.dataset.msgSendFail);
    }
    return data.item;
  }

  async function postDelete(url, failMessage) {
    const response = await fetch(url, {
      method: "POST",
      headers: csrfHeaders(),
      credentials: "same-origin",
    });
    let data = {};
    try {
      data = await response.json();
    } catch (err) {
      data = {};
    }
    if (!response.ok || !data.ok) {
      throw new Error(data.error || failMessage);
    }
  }

  if (addImageBtn && imageInput) {
    addImageBtn.addEventListener("click", function () {
      showError("");
      if (images.length >= maxImages) {
        showError(root.dataset.msgImgLimit);
        return;
      }
      imageInput.click();
    });
    imageInput.addEventListener("change", async function () {
      const file = imageInput.files && imageInput.files[0];
      imageInput.value = "";
      if (!file) return;
      const localError = validateImage(file);
      if (localError) {
        showError(localError);
        return;
      }
      setBusy(true);
      try {
        const item = await postFile(root.dataset.addImageUrl, "file", file);
        if (item && item.id) images.push(item);
        showError("");
        render();
      } catch (err) {
        showError(err.message || root.dataset.msgSendFail);
      } finally {
        setBusy(false);
        updateButtons();
      }
    });
  }

  if (addVideoBtn && videoInput) {
    addVideoBtn.addEventListener("click", function () {
      showError("");
      if (videos.length >= maxVideos) {
        showError(root.dataset.msgVidLimit);
        return;
      }
      videoInput.click();
    });
    videoInput.addEventListener("change", async function () {
      const file = videoInput.files && videoInput.files[0];
      videoInput.value = "";
      if (!file) return;
      const localError = validateVideo(file);
      if (localError) {
        showError(localError);
        return;
      }
      setBusy(true);
      try {
        const item = await postFile(root.dataset.addVideoUrl, "video", file);
        if (item && item.id) videos.push(item);
        showError("");
        render();
      } catch (err) {
        showError(err.message || root.dataset.msgSendFail);
      } finally {
        setBusy(false);
        updateButtons();
      }
    });
  }

  if (imagesEl) {
    imagesEl.addEventListener("click", async function (event) {
      const button = event.target.closest("[data-delete-image]");
      if (!button) return;
      const imageId = button.getAttribute("data-delete-image");
      if (!imageId || !window.confirm(root.dataset.msgDelImg)) return;
      setBusy(true);
      try {
        await postDelete(withId(root.dataset.deleteImageUrl, imageId), root.dataset.msgDelFail);
        const index = images.findIndex(function (item) {
          return String(item.id) === String(imageId);
        });
        if (index >= 0) images.splice(index, 1);
        showError("");
        render();
      } catch (err) {
        showError(err.message || root.dataset.msgDelFail);
      } finally {
        setBusy(false);
        updateButtons();
      }
    });
  }

  if (videosEl) {
    videosEl.addEventListener("click", async function (event) {
      const button = event.target.closest("[data-delete-video]");
      if (!button) return;
      const videoId = button.getAttribute("data-delete-video");
      if (!videoId || !window.confirm(root.dataset.msgDelVid)) return;
      setBusy(true);
      try {
        await postDelete(withId(root.dataset.deleteVideoUrl, videoId), root.dataset.msgDelFail);
        const index = videos.findIndex(function (item) {
          return String(item.id) === String(videoId);
        });
        if (index >= 0) videos.splice(index, 1);
        showError("");
        render();
      } catch (err) {
        showError(err.message || root.dataset.msgDelFail);
      } finally {
        setBusy(false);
        updateButtons();
      }
    });
  }

  render();
})();
