const setupSlider = (element, interval = 4000) => {
  if (!element) return;
  const images = JSON.parse(element.dataset.images || "[]");
  if (!images.length) return;
  let index = 0;
  const transitionDuration = 1200;
  element.style.setProperty("--hero-image", `url('${images[0]}')`);

  setInterval(() => {
    index = (index + 1) % images.length;
    const nextImage = `url('${images[index]}')`;
    element.style.setProperty("--hero-next-image", nextImage);
    element.classList.add("is-transitioning");
    window.setTimeout(() => {
      element.style.setProperty("--hero-image", nextImage);
      element.classList.remove("is-transitioning");
    }, transitionDuration);
  }, interval);
};

const setupImageSwap = (element, interval = 4000) => {
  if (!element) return;
  const images = JSON.parse(element.dataset.images || "[]");
  const img = element.querySelector("img");
  if (!images.length || !img) return;
  let index = 0;
  setInterval(() => {
    index = (index + 1) % images.length;
    img.src = images[index];
  }, interval);
};

const observeReveal = () => {
  const elements = document.querySelectorAll(".reveal");
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
        }
      });
    },
    { threshold: 0.2 }
  );
  elements.forEach((el) => observer.observe(el));
};

const setupNavToggle = () => {
  const toggle = document.querySelector(".nav-toggle");
  const links = document.querySelector(".nav-links");
  if (!toggle || !links) return;
  toggle.addEventListener("click", () => {
    links.classList.toggle("open");
  });
};

const setupRegisterToggle = () => {
  const trigger = document.querySelector("[data-toggle='register-form']");
  const form = document.getElementById("register-form");
  const loginForm = document.getElementById("login-form");
  if (!trigger || !form || !loginForm) return;
  trigger.addEventListener("click", () => {
    form.classList.toggle("hidden");
    loginForm.classList.toggle("hidden");
  });
};

const setupAstrofotoUploadToggle = () => {
  const trigger = document.querySelector("[data-toggle='astrofoto-upload']");
  const form = document.getElementById("astrofoto-upload");
  if (!trigger || !form) return;
  trigger.addEventListener("click", () => {
    form.classList.toggle("hidden");
    if (!form.classList.contains("hidden")) {
      form.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
};

const setupAstrofotoVersionFields = () => {
  const container = document.querySelector("[data-astrofoto-versions-form]");
  if (!container) return;
  const list = container.querySelector("[data-astrofoto-versions-list]");
  const addButton = container.querySelector("[data-astrofoto-add-version]");
  if (!list || !addButton) return;

  const createField = () => {
    const wrapper = document.createElement("div");
    wrapper.className = "astrofoto-version-field";
    wrapper.innerHTML = `
      <label>Imagen de versión
        <input type="file" name="version_files" accept="image/*" required />
      </label>
      <label>Descripción de versión
        <textarea name="version_descriptions" rows="2"></textarea>
      </label>
      <div class="astrofoto-version-actions">
        <button class="button ghost small" type="button" data-remove-version>Quitar versión</button>
      </div>
    `;
    const removeButton = wrapper.querySelector("[data-remove-version]");
    if (removeButton) {
      removeButton.addEventListener("click", () => wrapper.remove());
    }
    return wrapper;
  };

  addButton.addEventListener("click", () => {
    list.appendChild(createField());
  });
};

const setupAstrofotoVersionsGallery = () => {
  const gallery = document.querySelector("[data-astrofoto-versions]");
  if (!gallery) return;
  const mainImage = document.querySelector("[data-astrofoto-main]");
  const description = document.querySelector("[data-astrofoto-description]");
  const openLink = document.querySelector(".photo-meta a.button.ghost");
  if (!mainImage) return;

  gallery.addEventListener("click", (event) => {
    const card = event.target.closest("[data-astrofoto-version]");
    if (!card) return;
    const imageUrl = card.dataset.imageUrl;
    if (!imageUrl) return;
    mainImage.src = imageUrl;
    if (openLink) {
      openLink.href = imageUrl;
    }
    if (description) {
      description.textContent = card.dataset.description || "";
    }
  });
};

const setupAstrofotoGalleryFilters = () => {
  const gallery = document.querySelector("[data-astrofoto-gallery]");
  if (!gallery) return;
  const cards = Array.from(gallery.querySelectorAll("[data-astrofoto-card]"));
  const authorSelect = document.querySelector("[data-astrofoto-filter='author']");
  const dateInput = document.querySelector("[data-astrofoto-filter='date']");
  const resetButton = document.querySelector("[data-astrofoto-filter-reset]");
  const pagination = document.querySelector("[data-astrofoto-pagination]");
  const toggleButton = document.querySelector("[data-astrofoto-filter-toggle]");
  const filters = document.querySelector("[data-astrofoto-filters]");
  const pageSize = 16;

  const normalize = (value) => (value || "").trim().toLowerCase();

  const updatePagination = (totalPages, currentPage) => {
    if (!pagination) return;
    pagination.innerHTML = "";
    if (totalPages <= 1) {
      pagination.classList.add("is-hidden");
      return;
    }
    pagination.classList.remove("is-hidden");
    for (let page = 1; page <= totalPages; page += 1) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = page;
      button.dataset.page = String(page);
      if (page === currentPage) {
        button.classList.add("is-active");
      }
      pagination.appendChild(button);
    }
  };

  const applyFilters = (page = 1) => {
    const authorValue = normalize(authorSelect?.value || "all");
    const dateValue = dateInput?.value || "";
    const filtered = cards.filter((card) => {
      const matchesAuthor =
        authorValue === "all" ||
        normalize(card.dataset.author) === authorValue;
      const matchesDate =
        !dateValue || (card.dataset.date || "").startsWith(dateValue);
      return matchesAuthor && matchesDate;
    });
    cards.forEach((card) => card.classList.add("is-hidden"));
    const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    const currentPage = Math.min(page, totalPages);
    const start = (currentPage - 1) * pageSize;
    const visible = filtered.slice(start, start + pageSize);
    visible.forEach((card) => card.classList.remove("is-hidden"));
    updatePagination(totalPages, currentPage);
  };

  if (authorSelect) {
    authorSelect.addEventListener("change", () => applyFilters(1));
  }
  if (dateInput) {
    dateInput.addEventListener("change", () => applyFilters(1));
  }
  if (resetButton) {
    resetButton.addEventListener("click", () => {
      if (authorSelect) authorSelect.value = "all";
      if (dateInput) dateInput.value = "";
      applyFilters(1);
    });
  }
  if (pagination) {
    pagination.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button) return;
      const page = Number(button.dataset.page || "1");
      applyFilters(page);
    });
  }
  if (toggleButton && filters) {
    toggleButton.addEventListener("click", () => {
      filters.classList.toggle("is-collapsed");
    });
  }

  applyFilters(1);
};

setupSlider(document.querySelector(".hero-slider"));
setupImageSwap(document.querySelector(".mini-slider"));
setupNavToggle();
setupRegisterToggle();
setupAstrofotoUploadToggle();
setupAstrofotoVersionFields();
setupAstrofotoVersionsGallery();
setupAstrofotoGalleryFilters();
observeReveal();
