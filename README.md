# Measulor - 3D Body Measurements from Video

Measulor turns a short video of a person into a 3D model and body measurements, and charges for each scan with Paddle.

```
video ──► 3D model ──► measurements          payments (Paddle) gates every scan
```

| Module | Code | What it does |
| --- | --- | --- |
| 1. Video | `api/modules/video.py` | Validates uploads (type, size, 3–120 s), samples frames evenly across the whole clip, drops blurry or badly lit frames, resizes for speed. |
| 2. 3D model | `api/modules/reconstruction.py` | COLMAP (pycolmap) SIFT features, sequential matching and incremental mapping into a sparse point cloud, exported as `.ply`. |
| 3. Measurements | `api/modules/measurements.py` | Finds the person (camera ray focus and outlier removal), aligns the vertical axis from the camera poses, scales by the user's height, and measures circumferences and widths on horizontal slices. Lengths that a sparse cloud can't resolve are flagged as `estimated`. |
| 4. Payments | `api/modules/payments/` | Paddle Billing ₹199/month subscription: checkout link or Paddle.js overlay, server-side transaction verification, signed webhooks, refunds, and customer portal. |

`api/pipeline.py` chains modules 1–3; `api/jobs.py` runs each scan as a background job (refunding the scan if it fails).

## Payments (Paddle Billing)

Payments are switched off until Paddle is configured: without the Paddle variables the app opens straight to the video upload and scans are free. Setting `PADDLE_API_KEY`, `PADDLE_PRICE_ID` and a checkout (`PADDLE_CHECKOUT_URL` or `PADDLE_CLIENT_TOKEN`) turns them on; `PAYMENTS_REQUIRED=true|false` overrides this.

Plan: **₹199/month subscription** with unlimited scans while it's active. Users cancel or update their card in the Paddle customer portal ("Manage billing").

1. In Paddle, create a product with a **recurring monthly price of ₹199 (INR)**. Set its `pri_...` ID as `PADDLE_PRICE_ID`.
2. Create an **API key** with `transaction.read`, `customer.read` and `customer_portal_session.write` and set it as `PADDLE_API_KEY`.
3. Choose a checkout:
   - **Checkout link:** set `PADDLE_CHECKOUT_URL` to your Paddle checkout link (for example `https://pay.paddle.io/checkout/hsc_...`), and set its redirect URL to `https://<your-domain>/`. The Subscribe button opens this link. If the return URL carries `transaction_id` (or `transactionId`), the app unlocks automatically. Otherwise the user pastes the `txn_...` ID from their receipt into "Restore subscription". Hosted checkout links need Paddle's approval on live accounts.
   - **Overlay checkout:** set `PADDLE_CLIENT_TOKEN` (a client-side token) and Paddle.js opens the checkout on the page.
4. Add a **notification destination** pointing to `https://<your-domain>/api/payments/webhook` with events
   `transaction.paid`, `transaction.completed`, `subscription.*`, `adjustment.created`, `adjustment.updated`. Copy its secret key into `PADDLE_WEBHOOK_SECRET`.
5. Add your domain to Paddle's approved websites, and set `PADDLE_ENVIRONMENT=production` for live payments.

Flow: when a checkout completes, the app gets the `transaction_id` (from the Paddle.js event or the redirect query string) and sends it to `/api/payments/claim`. The server then fetches the transaction from Paddle and, if it is paid with the configured price, links that Paddle customer to the browser session. Webhooks keep the subscription status (active, past due, canceled) and refunds in sync. Users can restore access on another device with the `txn_...` ID from their Paddle receipt.

`PADDLE_PRICE_ID` can also point to a one-time price. Each purchase then grants `SCANS_PER_PURCHASE` scans.

## API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/` | Web app |
| GET | `/health` | Health check (DB connectivity) |
| POST | `/api/jobs` | Multipart `video` + `height_cm`. Returns `202 {job_id}` or `402` if payment is required |
| GET | `/api/jobs/<id>` | Job status, stage and results |
| GET | `/api/jobs/<id>/model.ply` | Download the 3D point cloud |
| GET | `/api/payments/config` | Paddle.js settings and the session's entitlement |
| POST | `/api/payments/claim` | `{transaction_id}` → link a paid checkout to this session |
| POST | `/api/payments/portal` | Paddle customer portal link |
| POST | `/api/payments/webhook` | Paddle webhooks (signature verified) |

## Running locally

Python 3.10 or 3.11.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python main.py      # http://localhost:5000, no payment needed until Paddle is configured
pytest
```

For checkout testing, use Paddle **sandbox** credentials and leave `PAYMENTS_REQUIRED` unset.

## Frontend demo (GitHub Pages)

`python scripts/build_pages.py site` builds a static, demo-mode copy of the UI (sample results, nothing is uploaded) into `site/`. `.github/workflows/pages.yml` publishes it to the `gh-pages` branch on every push to `main`.

## Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/kk590/measulor)

The button reads `render.yaml`: one Docker web service (Standard plan, Singapore) with a 10 GB disk at `/app/data` and a generated `SECRET_KEY`. Leave the Paddle fields empty to launch with free scans; fill them in later under **Environment** and payments switch on after the redeploy. Then point the Paddle webhook at `https://<your-service>.onrender.com/api/payments/webhook`.

## Deploying

```bash
docker build -t measulor .
docker run -p 5000:5000 --env-file .env -v measulor-data:/app/data measulor
```

- `render.yaml`, `railway.json` and `docker-compose.yml` (with `nginx.conf` for TLS) all use the Dockerfile.
- Keep `/app/data` on a persistent disk (uploads, 3D models, SQLite DB), or set `DATABASE_URL` to Postgres.
- Gunicorn runs a single worker process that owns the job queue (`WORKER_THREADS` scans in parallel). COLMAP is CPU heavy, so use an instance with 4+ vCPUs and 4+ GB RAM.
- The app refuses to start in production without `SECRET_KEY`, or with payments on but Paddle variables missing.

## Recording tips for accurate results

- Tight clothing, A-pose, good lighting and a textured background.
- Another person walks slowly in a full circle, keeping the whole body in frame, for 10–60 seconds.

## License

MIT
