// Browser APIs: MDN getUserMedia and requestVideoFrameCallback; see docs/REFERENCES.md.
const $ = (id) => document.getElementById(id);
const video = $("preview");
const claimToken = location.pathname === "/claim" ? location.hash.slice(1) : undefined;
let stream = null, running = false, aborted = false, busy = false;
let lastBundle = null;
const colorNames = ["red", "green", "blue", "yellow"];

function status(message, error = false) {
  $("status").textContent = message;
  $("status").classList.toggle("error", error);
}
function buttons() {
  $("enable").disabled = !!stream || busy || !$("consent").checked;
  $("start").disabled = !stream || !$("consent").checked || busy;
  $("stop-camera").disabled = !stream || busy;
}
function swatches(id, colors = [], palette = {}, expected = null) {
  $(id).replaceChildren();
  for (let i = 0; i < 10; i++) {
    const color = colors[i];
    const swatch = document.createElement("div");
    swatch.className = `swatch${color ? "" : " empty"}`;
    if (color && palette[color]) swatch.style.backgroundColor = `rgb(${palette[color].join(",")})`;
    if (expected && color) {
      const match = color === expected[i];
      swatch.dataset.mark = match ? "✓" : "×";
      swatch.classList.toggle("miss", !match);
    }
    swatch.role = "img";
    swatch.setAttribute("aria-label", `Slot ${i + 1}: ${color || "not measured"}${expected && color ? color === expected[i] ? ", match" : ", miss" : ""}`);
    swatch.title = swatch.getAttribute("aria-label");
    $(id).append(swatch);
  }
}
swatches("issued"); swatches("decoded"); buttons();

function stopCamera() {
  stream?.getTracks().forEach((track) => track.stop());
  stream = null; video.srcObject = null; video.hidden = true;
  $("placeholder").hidden = false;
  $("camera-state").textContent = "Camera off";
  buttons();
}
$("stop-camera").addEventListener("click", stopCamera);
$("consent").addEventListener("change", () => {
  if (!$("consent").checked && !busy) stopCamera();
  buttons();
});
$("enable").addEventListener("click", async () => {
  if (!navigator.mediaDevices?.getUserMedia) {
    status("Open this page at localhost on the laptop, or use a trusted HTTPS address on a phone. Camera access requires a secure context.", true);
    return;
  }
  busy = true; buttons(); status("Allow camera access in your browser to frame the item.");
  try {
    stream = await navigator.mediaDevices.getUserMedia({audio: false, video: {facingMode: "user", width: {ideal: 640}, height: {ideal: 480}, frameRate: {ideal: 30}}});
    if (!$("consent").checked) { stopCamera(); return; }
    video.srcObject = stream; await video.play();
    video.hidden = false; $("placeholder").hidden = true;
    const track = stream.getVideoTracks()[0];
    track.addEventListener("ended", () => { aborted = true; stopCamera(); status("Camera disconnected. Enable it again to retry.", true); });
    const settings = track.getSettings();
    $("camera-state").textContent = `${settings.width || video.videoWidth} × ${settings.height || video.videoHeight} · ${Math.round(settings.frameRate || 0)} fps`;
    status("Camera ready. Hold the item 15–40 cm away, then start the capture.");
  } catch (error) {
    stopCamera();
    const messages = {NotAllowedError: "Camera access was blocked. Allow it in your browser settings and enable the camera again.", NotFoundError: "No camera was found. Connect one and try again.", NotReadableError: "The camera is busy. Close other camera apps and try again."};
    status(messages[error.name] || `Camera could not start: ${error.message}`, true);
  } finally { busy = false; buttons(); }
});
$("alternative").addEventListener("click", () => {
  if (claimToken) {
    $("claim-panel").scrollIntoView({ block: "start" });
    $("claim-notice").textContent = "You can send a photo or statement without changing lights.";
    return;
  }
  stopCamera();
  status("Changing lights are optional. In the future claims flow, this path will request a return-based resolution. No return request or payment is sent in this physics experiment.");
});
$("abort").addEventListener("click", () => { aborted = true; });
document.addEventListener("keydown", (event) => { if (event.key === "Escape") aborted = true; if (running && event.key === "Tab") { event.preventDefault(); $("abort").focus(); } });
document.addEventListener("visibilitychange", () => { if (document.hidden && running) aborted = true; });
window.addEventListener("pagehide", () => { aborted = true; stopCamera(); });

async function post(path, payload) {
  const response = await fetch(path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)});
  if (!response.ok) {
    const text = await response.text();
    let detail; try { detail = JSON.parse(text).detail; } catch { detail = text; }
    throw new Error(typeof detail === "string" ? detail : `Request failed (${response.status}). Start a fresh capture.`);
  }
  return response.json();
}
const tick = () => new Promise((resolve) => requestAnimationFrame(resolve));
async function waitUntil(target) {
  let now = await tick();
  while (now < target) {
    if (aborted) throw new Error("Capture stopped. Start a fresh capture when you are ready.");
    now = await tick();
  }
  if (aborted) throw new Error("Capture stopped. Start a fresh capture when you are ready.");
  return now;
}

function sampleCamera(startTime, frames, times, frameMeta) {
  const canvas = document.createElement("canvas"); canvas.width = 160; canvas.height = 120;
  const context = canvas.getContext("2d", {alpha: false});
  let callbackId = null, timer = null;
  function sample(now, meta = {}) {
    if (!running) return;
    if (frames.length >= 500) { aborted = true; return; }
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    frames.push(canvas.toDataURL("image/jpeg", 0.82).split(",")[1]);
    // presentationTime is in the performance.now() domain; captureTime may be
    // unavailable. Keep presentation timing consistent; retain metadata separately.
    times.push((meta.presentationTime ?? now) - startTime);
    frameMeta.push({mediaTime: meta.mediaTime, presentedFrames: meta.presentedFrames,
      captureTime: meta.captureTime, callbackTime: now - startTime});
    if (video.requestVideoFrameCallback) callbackId = video.requestVideoFrameCallback(sample);
  }
  if (video.requestVideoFrameCallback) callbackId = video.requestVideoFrameCallback(sample);
  else timer = setInterval(() => {
    if (frameMeta.at(-1)?.mediaTime !== video.currentTime) sample(performance.now(), {mediaTime: video.currentTime});
  }, 1000 / 30);
  return () => { if (callbackId !== null) video.cancelVideoFrameCallback(callbackId); if (timer) clearInterval(timer); };
}

async function upload(bundle) {
  status("Analyzing the recorded light response on the local server…");
  const result = await post("/api/captures", bundle);
  displayResult(result, bundle.challenge);
  if (claimToken) document.dispatchEvent(new CustomEvent("pol-capture", {detail: {id: result.id}}));
  lastBundle = null;
}
$("start").addEventListener("click", async () => {
  if (!stream || busy || !$("consent").checked) return;
  busy = true; buttons(); aborted = false; lastBundle = null; $("result").hidden = true;
  $("sequence-state").textContent = "Preparing fresh challenge";
  swatches("issued"); swatches("decoded");
  let stopSampling = () => {};
  const conditions = {object: $("object").value, lighting: $("lighting").value,
    distance_cm: Number($("distance").value), source: "browser-camera-physical-label-unverified"};
  try {
    const challenge = await post("/api/challenges", {reduced: $("reduced").checked, claim_token: claimToken});
    const field = $("light-field"); field.hidden = false;
    $("inset").prepend(video); $("abort").focus();
    field.style.backgroundColor = "rgb(150,150,150)";
    const startTime = performance.now();
    const frames = [], times = [], frameMeta = [], paint = [];
    running = true;
    stopSampling = sampleCamera(startTime, frames, times, frameMeta);
    let deadline = startTime + challenge.lead_ms;
    const sequence = challenge.calibration.concat(challenge.body);
    for (let i = 0; i < sequence.length; i++) {
      const now = await waitUntil(deadline);
      // Stamp actual rAF style mutation; this approximates paint, not photodiode
      // measurement. Schedule from actual mutation so lag never creates bursts.
      field.style.backgroundColor = `rgb(${challenge.palette[sequence[i]].join(",")})`;
      paint.push(now - startTime);
      $("live-step").textContent = i < challenge.calibration.length ? `Calibration ${i + 1} of ${challenge.calibration.length}` : `Challenge ${i - challenge.calibration.length + 1} of 10`;
      deadline = now + challenge.slot_ms;
    }
    paint.push(await waitUntil(deadline) - startTime);
    // Hold final color for the latency tail. Do not log a new slot or decode it.
    await waitUntil(performance.now() + 550);
    running = false; stopSampling(); field.hidden = true;
    $("camera-shell").prepend(video);
    lastBundle = {challenge, frames, times_ms: times, paint_ms: paint,
      device_meta: {settings: stream.getVideoTracks()[0].getSettings(),
        user_agent: navigator.userAgent, frame_callback: !!video.requestVideoFrameCallback,
        frame_metadata: frameMeta, exposure_lock: "not attempted in physics spike"}, conditions};
    // Release the hardware immediately after recording; analysis needs no camera.
    stopCamera();
    await upload(lastBundle);
  } catch (error) {
    status(error.message, true); $("sequence-state").textContent = "Capture not completed";
    if (lastBundle) {
      const blob = new Blob([JSON.stringify(lastBundle)], {type: "application/json"});
      const link = document.createElement("a"); link.href = URL.createObjectURL(blob);
      link.download = "pol-recovery.json"; link.textContent = "Save raw capture to recover offline";
      link.className = "secondary"; $("status").append(document.createElement("br"), link);
    }
  } finally {
    running = false; stopSampling(); $("light-field").hidden = true;
    $("camera-shell").prepend(video);
    stopCamera(); busy = false; buttons();
    const focusTarget = $("result").hidden ? $("enable") : $("result-title");
    focusTarget.tabIndex = -1; focusTarget.focus({preventScroll: true});
  }
});

function displayResult(result, challenge) {
  const report = result.report;
  swatches("issued", challenge.body, challenge.palette);
  swatches("decoded", report.decoded, challenge.palette, challenge.body);
  $("sequence-state").textContent = `${report.matches} of 10 slots matched`;
  const titles = {VERIFIED: "The light sequence matched.", FAILED: "The signal did not match.", INCONCLUSIVE: "The result is inconclusive."};
  $("result-title").textContent = titles[report.verdict];
  $("result-reason").textContent = report.reason;
  $("download").href = result.download;
  $("metrics").replaceChildren();
  const metrics = [["Matched slots", `${report.matches} / 10`], ["Guessing-null chance", report.chance_p.toExponential(2)], ["Signal correlation", report.correlation.toFixed(3)], ["Analysis time", `${Math.round(report.elapsed_ms)} ms`]];
  for (const [label, value] of metrics) {
    const group = document.createElement("div");
    const dt = document.createElement("dt"), dd = document.createElement("dd");
    dt.textContent = label; dd.textContent = value; group.append(dt, dd); $("metrics").append(group);
  }
  const ns = "http://www.w3.org/2000/svg"; $("trace").replaceChildren();
  $("trace-empty").hidden = report.trace.length > 0;
  $("trace").hidden = report.trace.length === 0;
  if (report.trace.length) {
    const first = report.trace[0].t_ms, duration = report.trace.at(-1).t_ms - first || 1;
    const values = report.trace.flatMap((p) => [p.r, p.g]);
    const min = Math.min(...values) - 0.005, range = Math.max(...values) - min + 0.005;
    for (const [channel, color] of [["r", "#9c4256"], ["g", "#26715b"]]) {
      const path = document.createElementNS(ns, "polyline");
      path.setAttribute("points", report.trace.map((p) => `${12 + (p.t_ms - first) / duration * 576},${118 - (p[channel] - min) / range * 106}`).join(" "));
      path.setAttribute("fill", "none"); path.setAttribute("stroke", color); path.setAttribute("stroke-width", "1.8"); $("trace").append(path);
    }
  }
  const heat = $("heatmap"), ctx = heat.getContext("2d");
  ctx.clearRect(0, 0, heat.width, heat.height);
  if (report.heatmap.length) {
    heat.height = report.heatmap.length; heat.width = report.heatmap[0].length;
    const max = Math.max(0.0001, ...report.heatmap.flat());
    report.heatmap.forEach((row, y) => row.forEach((v, x) => {
      const t = v / max; ctx.fillStyle = `rgb(${Math.round(235 - t * 186)},${Math.round(242 - t * 151)},${Math.round(249 - t * 81)})`; ctx.fillRect(x, y, 1, 1);
    }));
  }
  $("result").hidden = false;
  $("result").scrollIntoView({block: "nearest", behavior: "instant"});
  status("Analysis complete. Download the capture within 10 minutes to keep the data.");
}
