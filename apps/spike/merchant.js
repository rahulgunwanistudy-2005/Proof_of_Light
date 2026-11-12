import { api, download, money, node, withButton } from "./workspace.js";

const get = (id) => document.getElementById(id);
const notices = get("notice");
const detail = get("case-detail");
let token = "";
let activeId = null;
let imageUrl = null;
let renderVersion = 0;

function notice(value, error = false) {
  notices.textContent = value;
  notices.classList.toggle("error", error);
}

function request(path, options = {}) {
  return api(`/api/review${path}`, { ...options, token });
}

function post(path, body = {}) {
  return request(path, { method: "POST", body });
}

function button(label, task, style = "secondary") {
  const element = node("button", label, style);
  element.type = "button";
  element.addEventListener("click", () => withButton(element, task, (msg) => notice(msg, true)));
  return element;
}

function sheet(title) {
  const element = node("section", undefined, "sheet");
  element.append(node("h2", title));
  return element;
}

function pairs(parent, entries) {
  const list = node("dl", undefined, "detail-pairs");
  for (const [label, value] of entries) list.append(node("dt", label), node("dd", value));
  parent.append(list);
}

async function refresh(select = activeId) {
  const [cases, orders, catalog] = await Promise.all([request("/cases"), request("/shop-orders"), api("/api/shop")]);
  const disputes = get("disputes");
  disputes.hidden = !catalog.sandbox_ready;
  disputes.replaceChildren(node("h2", "PayPal disputes"));
  disputes.append(button("Load sandbox disputes", async () => {
    const items = await request("/disputes");
    const results = node("div", undefined, "stack");
    for (const item of items.filter((entry) => entry.id)) {
      results.append(button(`${item.id} · ${item.status || "Open"}`, async () => {
        const imported = await post(`/disputes/${encodeURIComponent(item.id)}/import`);
        await refresh(imported.id);
      }));
    }
    if (!items.length) results.append(node("p", "No sandbox disputes found.", "notice"));
    disputes.querySelector(".stack")?.remove();
    disputes.append(results);
  }));
  const list = get("case-list");
  list.replaceChildren();
  for (const entry of [...cases].reverse()) {
    const element = button(entry.snapshot.paypal_order_id, () => refresh(entry.id));
    element.setAttribute("aria-current", String(entry.id === select));
    list.append(element);
  }
  if (!cases.length) list.append(node("p", "Create a practice case to try the review flow.", "notice"));
  const orderList = get("orders");
  orderList.hidden = orders.length === 0;
  orderList.replaceChildren(node("h2", "Completed sandbox orders"));
  for (const order of orders) {
    const row = node("div", undefined, "action-card");
    row.append(button(`Open case for ${order.paypal_order_id}`, async () => {
      const created = await post(`/shop-orders/${order.checkout_id}/case`);
      await refresh(created.id);
    }));
    if (order.tracking) {
      row.append(node("p", `${order.tracking.carrier} · ${order.tracking.tracking_number}`));
    } else {
      const tracking = node("details");
      tracking.append(node("summary", "Add shipment tracking"));
      const form = node("form", undefined, "stack");
      const carrier = node("input");
      carrier.required = true;
      carrier.placeholder = "Carrier code, e.g. UPS";
      carrier.setAttribute("aria-label", "Carrier code");
      const number = node("input");
      number.required = true;
      number.placeholder = "Tracking number";
      number.setAttribute("aria-label", "Tracking number");
      const submit = node("button", "Save tracking in PayPal", "secondary");
      form.append(carrier, number, submit);
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        withButton(submit, async () => {
          await post(`/shop-orders/${order.checkout_id}/tracking`, { carrier: carrier.value.trim().toUpperCase(), tracking_number: number.value.trim() });
          await refresh();
          notice("Shipment tracking saved in PayPal sandbox.");
        }, (message) => notice(message, true));
      });
      tracking.append(form);
      row.append(tracking);
    }
    orderList.append(row);
  }
  if (select && cases.some((entry) => entry.id === select)) await showCase(select);
  else detail.replaceChildren();
}

function renderLight(parent, light) {
  const outcomes = { VERIFIED: "Signal matched", FAILED: "Signal did not match", INCONCLUSIVE: "Insufficient signal" };
  parent.append(node("p", outcomes[light.verdict] || "Photo or statement without a light measurement."));
  if (light.verdict) parent.append(node("p", "The light response gives context for review. Item authenticity is unverified.", "notice"));
  for (const [label, colors] of [["Issued", light.expected], ["Read", light.decoded]]) {
    if (!Array.isArray(colors)) continue;
    const row = node("div", undefined, "chip-row");
    row.setAttribute("aria-label", `${label} sequence`);
    const palette = { red: "#cd7777", yellow: "#d7bd78", green: "#80aa92", blue: "#799cc1" };
    for (const color of colors) {
      const chip = node("span");
      chip.style.backgroundColor = palette[color] || "#e7edf5";
      chip.title = `${label} ${color || "unknown"}`;
      row.append(chip);
    }
    parent.append(row);
  }
}

async function showCase(id) {
  activeId = id;
  const rendering = ++renderVersion;
  const [record, evidence] = await Promise.all([request(`/cases/${id}`), request(`/cases/${id}/evidence`)]);
  if (rendering !== renderVersion) return;
  if (imageUrl) URL.revokeObjectURL(imageUrl);
  imageUrl = null;
  detail.replaceChildren();
  const context = sheet("Case details");
  pairs(context, [["Order", record.snapshot.paypal_order_id], ["Purchase", money(record.snapshot.amount_minor, record.snapshot.currency)],
    ["Capture", record.snapshot.capture_id || "Awaiting capture ID"], ["Dispute", record.snapshot.dispute_id || "No dispute attached"]]);
  const shipment = record.snapshot.shipment;
  if (shipment?.tracking_number) pairs(context, [["Tracking", `${shipment.carrier} · ${shipment.tracking_number}`]]);
  const dispute = record.snapshot.provider_dispute;
  if (dispute?.id) pairs(context, [["PayPal status", dispute.status || "Unknown"], ["Dispute stage", dispute.stage || "Unknown"], ["Seller response due", dispute.seller_due || "Unavailable"]]);
  const inviteSlot = node("div");
  const actions = node("div", undefined, "actions");
  actions.append(button("Create buyer link", async () => {
    const invite = await post(`/cases/${id}/invitations`);
    const url = new URL(invite.path, location.origin).href;
    const link = node("a", "Open buyer invitation");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    const copy = node("input");
    copy.readOnly = true;
    copy.value = url;
    copy.setAttribute("aria-label", "Buyer invitation link");
    copy.addEventListener("focus", () => copy.select());
    inviteSlot.replaceChildren(link, copy);
    notice("Buyer link created. Share it with the buyer. It accepts one submission.");
  }), button("Download evidence PDF", async () => download(await request(`/cases/${id}/packet.pdf`), `proof-of-light-${id}.pdf`)));
  context.append(actions, inviteSlot);
  detail.append(context);
  const evidenceSheet = sheet("Buyer evidence");
  if (evidence) {
    evidenceSheet.append(node("p", evidence.statement));
    if (evidence.has_image) {
      const image = node("img", undefined, "evidence-photo");
      image.alt = "Item evidence submitted by the buyer";
      evidenceSheet.append(image);
      request(`/cases/${id}/evidence/${evidence.id}.jpg`).then((blob) => {
        if (rendering !== renderVersion) return;
        imageUrl = URL.createObjectURL(blob);
        image.src = imageUrl;
      }).catch((error) => notice(error.message, true));
    }
    renderLight(evidenceSheet, evidence.light_report);
    if (evidence.assessment.model) {
      pairs(evidenceSheet, [["AI observation", evidence.assessment.visible_condition], ["Uncertainty", evidence.assessment.uncertainty], ["Follow-up view", evidence.assessment.follow_up]]);
    } else if (evidence.ai_consent) {
      evidenceSheet.append(button("Generate Gemini notes", async () => {
        await post(`/cases/${id}/assessment`);
        await showCase(id);
      }));
    }
  } else {
    evidenceSheet.append(node("p", "Waiting for the buyer’s statement or image.", "notice"));
  }
  detail.append(evidenceSheet);
  renderActions(record);
}

function renderActions(record) {
  const panel = sheet("Financial review");
  const { id, snapshot } = record;
  if (snapshot.dispute_id) {
    const paypal = node("a", "Open PayPal sandbox Resolution Center");
    paypal.href = "https://www.sandbox.paypal.com/disputes/";
    paypal.target = "_blank";
    paypal.rel = "noopener noreferrer";
    panel.append(node("p", "Use the Resolution Center to resolve this dispute.", "notice"), paypal);
  } else if (snapshot.capture_id && snapshot.currency === "USD") {
    const form = node("form", undefined, "stack");
    const amountLabel = node("label", "Refund amount (USD)");
    const amount = node("input");
    amount.type = "number";
    amount.min = "0.01";
    amount.step = "0.01";
    amount.max = String(snapshot.amount_minor / 100);
    amount.required = true;
    amountLabel.append(amount);
    const reasonLabel = node("label", "Reason for proposal");
    const reason = node("textarea");
    reason.required = true;
    reason.maxLength = 2000;
    reasonLabel.append(reason);
    const submit = node("button", "Prepare refund proposal", "secondary");
    form.append(amountLabel, reasonLabel, submit);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      withButton(submit, async () => {
        await post(`/cases/${id}/proposals`, { financial_action: { action: "refund_capture", amount_minor: Math.round(Number(amount.value) * 100), currency: "USD", target_id: snapshot.capture_id }, explanation: reason.value });
        await showCase(id);
        notice("Refund proposal ready for review.");
      }, (msg) => notice(msg, true));
    });
    panel.append(form);
  } else {
    panel.append(node("p", "A USD capture ID is required to prepare a sandbox refund.", "notice"));
  }
  for (const proposal of [...record.proposals].reverse()) {
    const section = node("div", undefined, "action-card");
    const action = proposal.payload;
    section.append(node("h3", `${money(action.amount_minor, action.currency)} ${action.action.replaceAll("_", " ")}`));
    pairs(section, [["Destination", action.target_id], ["Review", proposal.status.replaceAll("_", " ").toLowerCase()]]);
    if (proposal.status === "PENDING_REVIEW") {
      const label = node("label", undefined, "check");
      const confirm = node("input");
      confirm.type = "checkbox";
      label.append(confirm, document.createTextNode(" I reviewed the amount and destination."));
      const approve = button("Approve exact refund", async () => {
        const result = await post(`/proposals/${proposal.id}/approve`, { expected_payload_hash: proposal.payload_hash, expected_case_version: proposal.case_version, confirm: confirm.checked });
        await showCase(id);
        notice(snapshot.paypal_order_id.startsWith("PRACTICE-") ? "Practice approval saved." : result.message);
      }, "primary");
      approve.disabled = true;
      confirm.addEventListener("change", () => { approve.disabled = !confirm.checked; });
      section.append(label, approve, button("Reject proposal", async () => {
        await post(`/proposals/${proposal.id}/reject`, { reason: "Merchant declined the proposed refund." });
        await showCase(id);
      }));
    }
    panel.append(section);
  }
  for (const action of record.actions) {
    const section = node("div", undefined, "action-card");
    const states = { AWAITING_EXECUTOR: snapshot.paypal_order_id.startsWith("PRACTICE-") ? "Practice approval saved" : "Approved, awaiting send", COMPLETED: "PayPal sandbox refund completed", PAYPAL_PENDING: "PayPal refund pending", RECONCILE: "Check status in PayPal", PROVIDER_REJECTED: "PayPal rejected the request", STALE: "Approval invalidated by new evidence" };
    section.append(node("h3", states[action.status] || action.status));
    pairs(section, [["Amount", money(action.payload.amount_minor, action.payload.currency)], ["Request ID", action.request_id]]);
    if (action.provider_result?.refund_id) pairs(section, [["PayPal refund", action.provider_result.refund_id]]);
    if (action.status === "AWAITING_EXECUTOR" && action.payload.action === "refund_capture" && !snapshot.dispute_id && !snapshot.paypal_order_id.startsWith("PRACTICE-")) {
      section.append(button("Send approved sandbox refund", async () => {
        const result = await post(`/actions/${action.id}/send`);
        await showCase(id);
        notice(states[result.status] || result.status);
      }, "primary"));
    }
    panel.append(section);
  }
  detail.append(panel);
  const audit = sheet("Case history");
  const list = node("ol");
  for (const entry of record.audit) list.append(node("li", entry.event.event.replaceAll("_", " ")));
  audit.append(list);
  detail.append(audit);
}

get("login").addEventListener("submit", (event) => {
  event.preventDefault();
  token = get("merchant-token").value.trim();
  withButton(event.submitter, async () => {
    await refresh();
    get("login").reset();
    get("login").hidden = true;
    get("workspace").hidden = false;
    notice("");
  }, (msg) => notice(msg, true));
});
get("refresh").addEventListener("click", (event) => withButton(event.currentTarget, () => refresh(), (msg) => notice(msg, true)));
get("sign-out").addEventListener("click", () => location.reload());
get("new-demo").addEventListener("click", (event) => withButton(event.currentTarget, async () => {
  const id = crypto.randomUUID().slice(0, 8).toUpperCase();
  const created = await post("/cases", { paypal_order_id: `PRACTICE-${id}`, capture_id: `PRACTICE-${id}`, amount_minor: 4800, currency: "USD" });
  await refresh(created.id);
}, (msg) => notice(msg, true)));
get("new-case").addEventListener("submit", (event) => {
  event.preventDefault();
  const fields = new FormData(event.currentTarget);
  withButton(event.submitter, async () => {
    const created = await post("/cases", { paypal_order_id: fields.get("order"), capture_id: fields.get("capture") || null,
      dispute_id: fields.get("dispute") || null, amount_minor: Math.round(Number(fields.get("amount")) * 100), currency: "USD" });
    get("new-case").reset();
    await refresh(created.id);
  }, (msg) => notice(msg, true));
});
