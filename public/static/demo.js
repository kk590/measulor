(() => {
  const realFetch = window.fetch.bind(window);
  const KEY = "measulor.demoJobs";
  const PROFILE = {
    chest_circumference: [0.555, "measured"], waist_circumference: [0.465, "measured"],
    hip_circumference: [0.565, "measured"], thigh_circumference: [0.325, "estimated"],
    shoulder_width: [0.245, "measured"], hip_width: [0.21, "measured"],
    arm_length: [0.44, "measured"], torso_length: [0.3, "measured"],
    inseam: [0.45, "measured"], leg_length: [0.53, "estimated"],
  };
  let memory = {};
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || memory; } catch (_) { return memory; } };
  const save = (jobs) => { memory = jobs; try { localStorage.setItem(KEY, JSON.stringify(jobs)); } catch (_) {} };
  const json = (body, status = 200) => Promise.resolve(new Response(JSON.stringify(body), {
    status, headers: { "Content-Type": "application/json" },
  }));

  function job(id, spec) {
    const elapsed = (Date.now() - spec.started) / 1000;
    const stage = elapsed < 1 ? "photos" : elapsed < 2.5 ? "pose" : elapsed < 3.5 ? "measurements" : "done";
    const out = { id, stage, status: stage === "done" ? "completed" : "running", has_model: false };
    if (stage === "done") {
      const height = spec.height;
      const measurements = { height: { value_cm: height, method: "estimated" } };
      Object.entries(PROFILE).forEach(([key, [ratio, method]]) => {
        measurements[key] = { value_cm: Math.round(height * ratio * 10) / 10, method };
      });
      out.result = { unit: "cm", confidence: "high", photos_used: spec.count || 1, measurements };
    }
    return out;
  }

  window.fetch = (input, options = {}) => {
    const url = new URL(typeof input === "string" ? input : input.url, window.location.href);
    const path = url.pathname.replace(/^.*?(\/api\/)/, "/api/");
    if (!path.startsWith("/api/")) return realFetch(input, options);
    if (path === "/api/payments/config") {
      return json({ required: false, entitlement: { can_scan: true } });
    }
    if (path === "/api/jobs" && options.method === "POST") {
      const photos = options.body && options.body.getAll ? options.body.getAll("photos") : [];
      const id = `demo-${Date.now()}`;
      const height = 168 + Math.floor(Math.random() * 12);
      const jobs = load();
      jobs[id] = { started: Date.now(), height, count: photos.length || 1 };
      save(jobs);
      return json({ success: true, job_id: id, entitlement: {} }, 202);
    }
    const match = path.match(/^\/api\/jobs\/([\w-]+)$/);
    if (match) {
      const spec = load()[match[1]];
      return spec ? json({ success: true, job: job(match[1], spec) }) : json({ success: false, message: "Demo job expired" }, 404);
    }
    return json({ success: false, message: "Not available in the demo" }, 404);
  };
})();
