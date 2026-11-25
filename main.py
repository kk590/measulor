"""Local development server. Use gunicorn (see Dockerfile) in production."""

import os

from api.index import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("APP_ENV") != "production")
