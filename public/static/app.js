(() => {
  const $ = (id) => document.getElementById(id);
  const STAGES = ["photos", "pose", "measurements"];
  const STAGE_TEXT = {
    queued: "Waiting...",
    photos: "Reading your photos...",
    pose: "Detecting body pose landmarks...",
    measurements: "Estimating height & computing measurements...",
  };
  let pollTimer = null;

  function showError(message) {
    $("error").textContent = message;
    $("error").hidden = !message;
  }

  async function api(path, options = {}) {
    const response = await fetch(path, { credentials: "same-origin", ...options });
    let body = {};
    try { body = await response.json(); } catch (_) {}
    return { ok: response.ok, status: response.status, body };
  }

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
    const entries = Object.entries(result.measurements);
    entries.sort(([a], [b]) => (a === "height" ? -1 : b === "height" ? 1 : a.localeCompare(b)));
    entries.forEach(([key, m]) => {
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
    const n = result.photos_used;
    $("model-stats").textContent = n ? `Processed ${n} photo(s). Height estimated from pose.` : "";
    $("results").hidden = false;
  }

  async function poll(jobId) {
    $("submit-btn").disabled = true;
    $("progress").hidden = false;
    const { ok, body } = await api(`/api/jobs/${jobId}`);
    if (!ok) { finish(); showError(body.message || "Lost track of the job"); return; }
    const job = body.job;
    setStage(job.stage);
    $("status").textContent = STAGE_TEXT[job.stage] || "";
    if (job.status === "completed") { finish(); renderResults(job); return; }
    if (job.status === "failed") { finish(); showError(job.error); return; }
    pollTimer = setTimeout(() => poll(jobId), 800);
  }

  function finish() {
    clearTimeout(pollTimer);
    $("progress").hidden = true;
    $("submit-btn").disabled = false;
  }

  $("upload-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");
    $("results").hidden = true;
    const form = new FormData();
    const files = $("photos").files;
    if (!files || !files.length) { showError("Select at least one photo"); return; }
    for (let i = 0; i < files.length; i++) form.append("photos", files[i]);
    $("submit-btn").disabled = true;
    $("progress").hidden = false;
    setStage("photos");
    $("status").textContent = "Uploading photos...";
    const { ok, body } = await api("/api/jobs", { method: "POST", body: form });
    if (!ok) { finish(); showError(body.message || "Upload failed"); return; }
    poll(body.job_id);
  });
})();
