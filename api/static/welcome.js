(() => {
  const params = new URLSearchParams(window.location.search);
  const txn = params.get("transaction_id") || params.get("transactionId");
  const copy = document.getElementById("welcome-copy");
  const err = document.getElementById("welcome-error");

  async function claim(transactionId, attempt) {
    const res = await fetch("/api/payments/claim", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transaction_id: transactionId }),
    });
    const body = await res.json().catch(() => ({}));
    if (res.ok) {
      copy.textContent = "Your subscription is active. You can start measuring clients from photos.";
      return;
    }
    if (body.pending && attempt < 8) {
      copy.textContent = "Payment is confirming…";
      setTimeout(() => claim(transactionId, attempt + 1), 1500);
      return;
    }
    err.hidden = false;
    err.textContent = body.message || "Could not confirm payment. You can restore it from the app with your receipt.";
    copy.textContent = "Almost there — if checkout finished, restore with your transaction ID from the receipt.";
  }

  if (txn) claim(txn, 0);
  else copy.textContent = "Thanks for subscribing. Head back to the app to measure from photos.";
})();
