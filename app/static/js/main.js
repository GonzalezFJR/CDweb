const setupSlider = (element, interval = 4000) => {
  if (!element) return;
  const images = JSON.parse(element.dataset.images || "[]");
  if (!images.length) return;
  let index = 0;
  element.style.backgroundImage = `url('${images[0]}')`;
  element.style.backgroundSize = "cover";
  element.style.backgroundPosition = "center";

  setInterval(() => {
    index = (index + 1) % images.length;
    element.style.backgroundImage = `url('${images[index]}')`;
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
  if (!trigger || !form) return;
  trigger.addEventListener("click", () => {
    form.classList.toggle("hidden");
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

setupSlider(document.querySelector(".hero-slider"));
setupImageSwap(document.querySelector(".mini-slider"));
setupNavToggle();
setupRegisterToggle();
setupAstrofotoUploadToggle();
setupAstrofotoVersionFields();
setupAstrofotoVersionsGallery();
observeReveal();
