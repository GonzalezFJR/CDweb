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

setupSlider(document.querySelector(".hero-slider"));
setupImageSwap(document.querySelector(".mini-slider"));
setupNavToggle();
setupRegisterToggle();
setupAstrofotoUploadToggle();
observeReveal();
