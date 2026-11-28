(() => {
  const $ = (id) => document.getElementById(id);
  let state = {
    environment: null,
    clientToken: null,
    country: null,
    customerEmail: null,
    successPath: "/welcome",
    tiers: [],
    interval: "month",
    prices: {}, // priceId -> formattedTotals.total from Paddle
    ready: false,
  };

  function showError(msg) {
    const el = $("pricing-error");
    el.textContent = msg || "";
    el.hidden = !msg;
  }

  function setInterval(interval) {
    state.interval = interval;
    $("btn-month").classList.toggle("is-active", interval === "month");
    $("btn-year").classList.toggle("is-active", interval === "year");
    renderTiers();
  }

  $("btn-month").addEventListener("click", () => setInterval("month"));
  $("btn-year").addEventListener("click", () => setInterval("year"));

  function priceLabel(tier) {
    const id = tier.priceId[state.interval];
    if (!id) return "—";
    const formatted = state.prices[id];
    if (!formatted) return "…";
    // Use Paddle's formatted string only — never reformat.
    return formatted;
  }

  function renderTiers() {
    const grid = $("tier-grid");
    grid.replaceChildren();
    if (!state.tiers.length) {
      const p = document.createElement("p");
      p.className = "muted mono loading-copy";
      p.textContent = "No plans configured yet.";
      grid.appendChild(p);
      return;
    }
    state.tiers.forEach((tier) => {
      const card = document.createElement("article");
      card.className = "tier-card" + (tier.highlighted ? " is-featured" : "");
      const name = document.createElement("div");
      name.className = "tier-name";
      name.textContent = tier.name;
      const desc = document.createElement("p");
      desc.className = "tier-desc";
      desc.textContent = tier.description;
      const price = document.createElement("div");
      price.className = "tier-price";
      price.textContent = priceLabel(tier);
      const period = document.createElement("span");
      period.className = "muted";
      period.textContent = state.interval === "year" ? " / year" : " / month";
      if (state.prices[tier.priceId[state.interval]]) price.appendChild(period);
      const ul = document.createElement("ul");
      ul.className = "tier-features";
      (tier.features || []).forEach((f) => {
        const li = document.createElement("li");
        li.textContent = f;
        ul.appendChild(li);
      });
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn-glow";
      btn.textContent = "Subscribe";
      const priceId = tier.priceId[state.interval];
      btn.disabled = !priceId || !state.ready;
      btn.addEventListener("click", () => openCheckout(priceId));
      card.append(name, desc, price, ul, btn);
      grid.appendChild(card);
    });
  }

  async function openCheckout(priceId) {
    if (!priceId || !window.Paddle) {
      showError("Checkout is not ready yet.");
      return;
    }
    showError("");
    const payload = {
      items: [{ priceId, quantity: 1 }],
      settings: {
        displayMode: "overlay",
        variant: "one-page",
        successUrl: window.location.origin + state.successPath,
      },
    };
    if (state.customerEmail) {
      payload.customer = { email: state.customerEmail };
    }
    try {
      window.Paddle.Checkout.open(payload);
    } catch (err) {
      console.error(err);
      showError("Could not open checkout. Check the domain is approved in Paddle for live mode.");
    }
  }

  async function loadPrices(priceIds) {
    if (!window.Paddle || !priceIds.length) return;
    const items = priceIds.map((priceId) => ({ priceId, quantity: 1 }));
    const request = { items };
    // Only pass a real ISO country code — never OTHERS / unknown sentinels.
    if (state.country && /^[A-Z]{2}$/.test(state.country)) {
      request.address = { countryCode: state.country };
    }
    try {
      const preview = await window.Paddle.PricePreview(request);
      const map = {};
      const details = preview?.data?.details?.lineItems || preview?.details?.lineItems || [];
      details.forEach((line) => {
        const id = line.price?.id || line.priceId;
        const total = line.formattedTotals?.total;
        if (id && total) map[id] = total;
      });
      // Some SDK shapes return one preview per call — fall back per-id requests.
      if (!Object.keys(map).length) {
        for (const priceId of priceIds) {
          const one = { items: [{ priceId, quantity: 1 }] };
          if (request.address) one.address = request.address;
          const p = await window.Paddle.PricePreview(one);
          const line = (p?.data?.details?.lineItems || p?.details?.lineItems || [])[0];
          const total = line?.formattedTotals?.total;
          if (total) map[priceId] = total;
        }
      }
      state.prices = map;
    } catch (err) {
      console.error("PricePreview failed", err);
      showError("Could not load localised prices from Paddle.");
    }
  }

  async function init() {
    let body;
    try {
      const res = await fetch("/api/payments/pricing", { credentials: "same-origin" });
      body = await res.json();
      if (!res.ok || !body.success) {
        showError(body.message || "Pricing is not configured on the server.");
        return;
      }
    } catch (err) {
      showError("Could not reach pricing configuration.");
      return;
    }

    if (!body.environment) {
      showError("PADDLE_ENVIRONMENT is missing on the server.");
      return;
    }
    if (!body.client_token) {
      showError("PADDLE_CLIENT_TOKEN is missing on the server.");
      return;
    }

    state.environment = body.environment;
    state.clientToken = body.client_token;
    state.country = body.country || null;
    state.customerEmail = body.customer_email || null;
    state.successPath = body.success_path || "/welcome";
    state.tiers = body.tiers || [];

    if (!window.Paddle) {
      showError("Paddle.js failed to load.");
      return;
    }

    if (state.environment === "sandbox") {
      window.Paddle.Environment.set("sandbox");
    }
    // production: do not call Environment.set — live is default for live_ tokens

    window.Paddle.Initialize({
      token: state.clientToken,
      eventCallback: (event) => {
        if (event?.name === "checkout.completed") {
          const txn = event.data?.transaction_id;
          const url = state.successPath + (txn ? `?transaction_id=${encodeURIComponent(txn)}` : "");
          window.location.assign = url;
        }
      },
    });

    state.ready = true;
    const ids = body.price_ids || [];
    await loadPrices(ids);
    renderTiers();
  }

  init();
})();
