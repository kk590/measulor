(() => {
  const $ = (id) => document.getElementById(id);
  const STAGES = ["photos", "pose", "measurements"];
  const STAGE_TEXT = {
    queued: "Waiting for a free worker...",
    photos: "Reading your photos...",
    pose: "Detecting body pose landmarks...",
    measurements: "Computing measurements...",
  };
  let payment = { required: false };
  let pollTimer = null;

  function showError(message) {
    $("error").textContent = message;
    $("error").hidden = !message;
  }

  async function api(path, options = {}) {
    const response = await fetch(path, { credentials: "same-origin", ...options });
    let body = {};
    try { body = await response.json(); } catch (_) { /* non-JSON error */ }
    return { ok: response.ok, status: response.status, body };
  }

  function renderEntitlement(entitlement) {
    if (!payment.required) return;
    $("billing").hidden = false;
    let text = `Subscribe for ${payment.price_label} to get unlimited scans.`;
    if (entitlement.subscription_active) text = `Subscription active (${payment.price_label}): unlimited scans.`;
    else if (entitlement.scans_remaining > 0) text = `${entitlement.scans_remaining} scan(s) remaining.`;
    $("billing-status").textContent = text;
    $("portal-btn").hidden = !entitlement.customer;
    $("buy-btn").hidden = entitlement.subscription_active;
  }

  async function claim(transactionId, email = "", attempt = 0) {
    const { ok, status, body } = await api("/api/payments/claim", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transaction_id: transactionId, email }),
    });
    if (ok) { showError(""); renderEntitlement(body.entitlement); return; }
    if (status === 409 && attempt < 10) { setTimeout(() => claim(transactionId, email, attempt + 1), 2000); return; }
    if (body.email_required) {
      $("restore-details").open = true;
      $("restore-txn").value = transactionId;
      $("restore-email").focus();
    }
    showError(body.message || "Could not confirm your payment");
  }

  async function initPayments() {
    const { body } = await api("/api/payments/config");
    payment = body;
    if (!payment.required) return;
    $("buy-btn").textContent = `Subscribe \u2013 ${payment.price_label}`;
    renderEntitlement(payment.entitlement);
    claimFromRedirect();
    if (!window.Paddle || !payment.client_token) {
      if (!payment.checkout_url) {
        showError("Checkout is unavailable right now. Please try again later.");
        $("buy-btn").disabled = true;
      }
      return;
    }
    if (payment.environment === "sandbox") Paddle.Environment.set("sandbox");
    Paddle.Initialize({
      token: payment.client_token,
      eventCallback: (event) => {
        if (event.name === "checkout.completed" && event.data && event.data.transaction_id) {
          claim(event.data.transaction_id);
        }
      },
    });
  }

  function claimFromRedirect() {
    const params = new URLSearchParams(window.location.search);
    const transactionId = params.get("transaction_id") || params.get("transactionId");
    if (!transactionId) return;
    params.delete("transaction_id");
    params.delete("transactionId");
    const query = params.toString();
    window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""));
    claim(transactionId);
  }

  function hostedCheckoutUrl() {
    const url = new URL(payment.checkout_url);
    const isHosted = /(^|\.)pay\.paddle\.io$/.test(url.hostname);
    if (isHosted && payment.price_id && !url.searchParams.has("price_id")) {
      url.searchParams.set("price_id", payment.price_id);
    }
    return url.toString();
  }

  $("buy-btn").addEventListener("click", () => {
    if (payment.checkout_url) {
      window.location.href = hostedCheckoutUrl();
      return;
    }
    Paddle.Checkout.open({ items: [{ priceId: payment.price_id, quantity: 1 }] });
  });

  $("portal-btn").addEventListener("click", async () => {
    const { ok, body } = await api("/api/payments/portal", { method: "POST" });
    if (ok && body.url) window.open(body.url, "_blank", "noopener");
    else showError(body.message || "Could not open billing portal");
  });

  const dropzone = $("dropzone");
  $("photos").addEventListener("change", () => {
    const files = $("photos").files;
    dropzone.classList.toggle("has-file", Boolean(files && files.length));
    $("dz-title").textContent = files && files.length
      ? `${files.length} photo${files.length > 1 ? "s" : ""} selected`
      : "Drop photos here or browse";
  });
  ["dragenter", "dragover"].forEach((type) => dropzone.addEventListener(type, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragover");
  }));
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragover");
    if (!event.dataTransfer || !event.dataTransfer.files.length) return;
    $("photos").files = event.dataTransfer.files;
    $("photos").dispatchEvent(new Event("change"));
  });

  $("restore-form").addEventListener("submit", (event) => {
    event.preventDefault();
    claim($("restore-txn").value.trim(), $("restore-email").value.trim());
  });

  function setStage(stage) {
    const current = STAGES.indexOf(stage);
    document.querySelectorAll("#steps li").forEach((li) => {
      const index = STAGES.indexOf(li.dataset.stage);
      li.classList.toggle("done", stage === "done" || (current >= 0 && index < current));
      li.classList.toggle("active", index === current);
    });
  }

  function label(key) {
    return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function renderResults(job) {
    const result = job.result;
    const tbody = $("measurements");
    tbody.replaceChildren();
    Object.entries(result.measurements).forEach(([key, m]) => {
      const row = document.createElement("tr");
      const name = document.createElement("td");
      name.textContent = label(key);
      const value = document.createElement("td");
      value.textContent = `${m.value_cm} cm`;
      const method = document.createElement("td");
      const tag = document.createElement("span");
      tag.className = `tag ${m.method}`;
      tag.textContent = m.method;
      method.appendChild(tag);
      row.append(name, value, method);
      tbody.appendChild(row);
    });
    $("confidence").textContent = `Confidence: ${result.confidence}`;
    const n = result.photos_used || result.photos?.count;
    $("model-stats").textContent = n ? `Processed ${n} photo(s).` : "";
    $("results").hidden = false;
  }

  const JOB_KEY = "measulor.activeJob";

  function remember(jobId) {
    try {
      if (jobId) localStorage.setItem(JOB_KEY, jobId);
      else localStorage.removeItem(JOB_KEY);
    } catch (_) { /* storage blocked */ }
  }

  async function poll(jobId) {
    remember(jobId);
    $("submit-btn").disabled = true;
    $("progress").hidden = false;
    const { ok, body } = await api(`/api/jobs/${jobId}`);
    if (!ok) { finish(); showError(body.message || "Lost track of the job"); return; }
    const job = body.job;
    setStage(job.stage);
    $("status").textContent = STAGE_TEXT[job.stage] || "";
    if (job.status === "completed") { finish(); renderResults(job); return; }
    if (job.status === "failed") { finish(); showError(job.error); refreshEntitlement(); return; }
    pollTimer = setTimeout(() => poll(jobId), 1500);
  }

  function finish() {
    clearTimeout(pollTimer);
    remember(null);
    $("progress").hidden = true;
    $("submit-btn").disabled = false;
  }

  async function refreshEntitlement() {
    if (!payment.required) return;
    const { body } = await api("/api/payments/config");
    renderEntitlement(body.entitlement);
  }

  $("upload-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");
    $("results").hidden = true;
    const form = new FormData();
    const files = $("photos").files;
    if (!files || !files.length) {
      showError("Select at least one photo");
      return;
    }
    for (let i = 0; i < files.length; i++) form.append("photos", files[i]);
    form.append("height_cm", $("height").value);
    $("submit-btn").disabled = true;
    $("progress").hidden = false;
    $("status").textContent = "Uploading photos...";
    const { ok, body } = await api("/api/jobs", { method: "POST", body: form });
    if (!ok) {
      finish();
      showError(body.message || "Upload failed");
      if (body.payment_required) $("billing").scrollIntoView({ behavior: "smooth" });
      return;
    }
    renderEntitlement(body.entitlement);
    poll(body.job_id);
  });

  initPayments().catch(() => showError("Could not load billing information"));
  let activeJob = null;
  try { activeJob = localStorage.getItem(JOB_KEY); } catch (_) { /* storage blocked */ }
  if (activeJob) poll(activeJob);
})();
