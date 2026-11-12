import { api, withButton } from "./workspace.js";

const claimToken = location.pathname === "/claim" ? location.hash.slice(1) : "";
const panel = document.getElementById("claim-panel");
const form = document.getElementById("claim-form");
const notice = document.getElementById("claim-notice");
const photo = document.getElementById("claim-photo");
let capture = null;

function say(text, error = false) {
  notice.textContent = text;
  notice.classList.toggle("error", error);
}

function fileData(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(reader.result.split(",")[1]));
    reader.addEventListener("error", () => reject(new Error("The photo could not be read.")));
    reader.readAsDataURL(file);
  });
}

if (location.pathname === "/claim") {
  panel.hidden = false;
  document.title = "Send item evidence · Proof of Light";
  document.querySelector(".intro h1").textContent = "Send item evidence";
  document.querySelector(".intro p").textContent = "Describe what happened and choose how to show the item.";
  document.querySelector(".finding").hidden = true;
  try {
    const state = await api("/api/claim", { claimToken });
    form.hidden = state.submitted;
    say(state.submitted ? "The merchant already received your evidence." : "Add a statement and optionally attach one image or a guided capture.");
  } catch (error) {
    say(error.message, true);
  }

  document.addEventListener("pol-capture", ({ detail }) => {
    capture = detail.id;
    photo.value = "";
    say("Guided capture attached. Add your statement and send the evidence.");
    panel.scrollIntoView({ block: "start" });
  });
  document.getElementById("claim-guide").addEventListener("click", () => {
    document.getElementById("camera-shell").scrollIntoView({ block: "start" });
  });
  photo.addEventListener("change", () => {
    capture = null;
    say(photo.files.length ? "Photo selected." : "You can send a statement on its own.");
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const fields = new FormData(form);
    withButton(event.submitter, async () => {
      const selected = photo.files[0];
      if (selected?.size > 5 * 1024 * 1024) throw new Error("Choose a photo under 5 MB.");
      const result = await api("/api/claim/evidence", { method: "POST", claimToken,
        body: { statement: fields.get("statement"), capture_id: capture,
          photo: selected ? await fileData(selected) : null, ai_consent: fields.has("ai") },
      });
      form.reset();
      form.hidden = true;
      say(result.message);
    }, (message) => say(message, true));
  });
}
