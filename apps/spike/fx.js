// Page effects shared by every screen. Nothing here is required to use the app:
// without WebGL, IntersectionObserver or motion, the content stays static and readable.
import { mountLightStack } from "./fx/lightstack.js";

const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const finePointer = matchMedia("(pointer: fine)").matches;
document.documentElement.classList.add("fx");

// 3D light stack scenes. The fallback image stays until WebGL succeeds.
for (const canvas of document.querySelectorAll("canvas[data-scene]")) {
  try {
    const scene = mountLightStack(canvas, { preset: canvas.dataset.scene, reducedMotion });
    if (!scene) continue;
    canvas.closest("[data-stage]")?.classList.add("is-3d");
    const toggle = document.querySelector(`[data-light-show="${canvas.id}"]`);
    toggle?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-value]");
      if (!button) return;
      const on = button.dataset.value === "on";
      for (const option of toggle.querySelectorAll("button")) option.setAttribute("aria-pressed", String(option === button));
      toggle.closest("[data-stage-root]")?.classList.toggle("light-show", on);
      scene.setShow(on);
    });
    if (toggle) toggle.hidden = false;
  } catch (error) {
    console.warn("3D scene unavailable; showing the still image.", error);
  }
}

// Scroll reveal for static sections.
const revealed = document.querySelectorAll("[data-reveal]");
if ("IntersectionObserver" in window && !reducedMotion) {
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add("in");
      observer.unobserve(entry.target);
    }
  }, { rootMargin: "0px 0px -8% 0px" });
  revealed.forEach((element) => observer.observe(element));
} else {
  revealed.forEach((element) => element.classList.add("in"));
}

// Pointer tilt for cards, delegated so cards rendered later also respond.
if (finePointer && !reducedMotion) {
  let active = null;
  document.addEventListener("pointermove", (event) => {
    const card = event.target.closest?.("[data-tilt]");
    if (active && active !== card) reset(active);
    active = card;
    if (!card) return;
    const box = card.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width;
    const y = (event.clientY - box.top) / box.height;
    card.style.setProperty("--ry", `${(x - 0.5) * 9}deg`);
    card.style.setProperty("--rx", `${(0.5 - y) * 7}deg`);
    card.style.setProperty("--mx", `${x * 100}%`);
    card.style.setProperty("--my", `${y * 100}%`);
    card.classList.add("tilting");
  }, { passive: true });
  document.addEventListener("pointerleave", () => active && reset(active));
  function reset(card) {
    card.classList.remove("tilting");
    card.style.removeProperty("--rx");
    card.style.removeProperty("--ry");
  }
}

// Seamless marquee: duplicate the track once for the loop.
for (const track of document.querySelectorAll("[data-marquee]")) {
  const clone = track.cloneNode(true);
  clone.setAttribute("aria-hidden", "true");
  clone.removeAttribute("data-marquee");
  track.after(clone);
}

// Live provider status in the header, read from the public health check.
const chip = document.getElementById("sandbox-chip");
if (chip) {
  fetch("/health").then((response) => response.json()).then((health) => {
    const live = health.paypal === "sandbox configured";
    chip.dataset.state = live ? "live" : "practice";
    chip.lastChild.textContent = live ? "PayPal sandbox live" : "Practice mode";
  }).catch(() => { chip.hidden = true; });
}
