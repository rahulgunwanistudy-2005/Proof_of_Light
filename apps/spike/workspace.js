export async function api(path, { token, claimToken, practiceToken, method = "GET", body } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (claimToken) headers["X-Claim-Token"] = claimToken;
  if (practiceToken) headers["X-Practice-Token"] = practiceToken;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const result = await fetch(path, {
    method, headers, body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!result.ok) {
    const payload = await result.json().catch(() => ({}));
    const detail = typeof payload.detail === "string" ? payload.detail : "Check the fields and try again.";
    throw new Error(detail);
  }
  return result.headers.get("content-type")?.includes("application/json") ? result.json() : result.blob();
}

export function node(tag, value, className) {
  const element = document.createElement(tag);
  if (value !== undefined) element.textContent = value;
  if (className) element.className = className;
  return element;
}

export function money(minor, currency) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(minor / 100);
}

export async function withButton(button, work, onError) {
  button.disabled = true;
  try {
    await work();
  } catch (error) {
    onError(error.message);
  } finally {
    button.disabled = false;
  }
}

export function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
