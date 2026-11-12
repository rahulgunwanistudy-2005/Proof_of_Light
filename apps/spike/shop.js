import { api, money, node, withButton } from "./workspace.js";

const status = document.getElementById("shop-notice");
const cart = document.getElementById("checkout");
const products = document.getElementById("products");
const query = new URLSearchParams(location.search);

function notice(text, error = false) {
  status.textContent = text;
  status.classList.toggle("error", error);
}

function post(path, body = {}) {
  return api(path, { method: "POST", body });
}

function renderReturn(checkout) {
  cart.hidden = false;
  const heading = node("h2", "Complete sandbox checkout");
  const capture = node("button", "Capture approved payment", "primary");
  cart.replaceChildren(heading, node("p", "PayPal checks the buyer’s approval before capture."), capture);
  capture.addEventListener("click", () => withButton(capture, async () => {
    const order = await post(`/api/shop/orders/${checkout}/capture`);
    if (order.status === "COMPLETED") {
      cart.replaceChildren(node("h2", "Sandbox purchase completed"), node("p", `${money(order.amount_minor, order.currency)} · PayPal order ${order.paypal_order_id}`), node("p", `Capture ${order.capture_id}`));
      notice("The merchant can open a claim case from this order.");
      history.replaceState(null, "", "/shop");
    } else {
      notice(order.status === "RECONCILE" ? "Check the completed order in PayPal before trying again." : "PayPal still shows this order as awaiting buyer approval.", true);
    }
  }, (message) => notice(message, true)));
}

try {
  const catalog = await api("/api/shop");
  if (query.get("cancelled")) notice("Checkout cancelled.");
  else notice(catalog.sandbox_ready ? "Sandbox mode uses PayPal test accounts." : "Add PayPal sandbox credentials to enable checkout.");
  const checkout = query.get("checkout");
  if (checkout && /^[a-f0-9]{32}$/.test(checkout)) renderReturn(checkout);
  for (const [index, item] of catalog.products.entries()) {
    const card = node("article", undefined, "sheet");
    const swatch = node("div", undefined, `product-swatch ${["mug", "bowl", "plate"][index]}`);
    swatch.setAttribute("aria-hidden", "true");
    const pay = node("button", "Continue to PayPal", "primary");
    pay.disabled = !catalog.sandbox_ready;
    const operation = crypto.randomUUID().replaceAll("-", "");
    pay.addEventListener("click", () => withButton(pay, async () => {
      const order = await post("/api/shop/orders", { sku: item.sku, checkout_id: operation });
      location.assign(order.approval_url);
    }, (message) => notice(message, true)));
    card.append(swatch, node("h2", item.name), node("p", money(item.amount_minor, item.currency)), pay);
    products.append(card);
  }
} catch (error) {
  notice(error.message, true);
}
