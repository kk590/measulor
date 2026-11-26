# Measulor - Body Measurements from Photos

Measulor turns full-body photos into body measurements (cm), with optional Paddle billing.

```
photos ──► pose landmarks ──► measurements          payments (Paddle) gates every scan
```

| Module | Code | What it does |
| --- | --- | --- |
| 1. Photos | `api/modules/photos.py` | Validates image uploads (JPG/PNG/WebP), resizes for speed. |
| 2. Pose + measure | `api/modules/photo_measurements.py` | MediaPipe Pose landmarks scaled by the user's height; widths measured, circumferences estimated where needed. |
| 3. Payments | `api/modules/payments/` | Optional Paddle Billing subscription / scan credits. |

`api/pipeline.py` runs photos → measurements; `api/jobs.py` runs each scan as a background job.

## Deploy on Vercel (demo UI)

`vercel.json` builds the static demo (`python scripts/build_pages.py public`) on every push. Open the production URL — **photos → measurements**, no license page, sample results in demo mode.

Full MediaPipe processing needs a Python host (Render/Docker). Vercel serves the interactive demo frontend.

## Deploy on Render (full backend)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/kk590/measulor)

Use **Web Service + Docker**, set `SECRET_KEY`, mount disk at `/app/data`, and set `PAYMENTS_REQUIRED=false` until Paddle is configured.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python main.py
pytest
```

## License

MIT
