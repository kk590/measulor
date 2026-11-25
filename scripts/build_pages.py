"""Build the static GitHub Pages demo (frontend only, sample results) into the given directory."""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANNER = ('<div class="demo-banner mono">DEMO MODE &middot; frontend preview with sample results &middot; '
          'no video is uploaded or processed</div>')


def build(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    html = (ROOT / "api/templates/index.html").read_text()
    html = html.replace("{{ url_for('static', filename='app.css') }}", "static/app.css")
    html = html.replace("{{ url_for('static', filename='app.js') }}", "static/app.js")
    html = html.replace('<script src="https://cdn.paddle.com/paddle/v2/paddle.js" defer></script>',
                        '<script src="static/demo.js" defer></script>')
    html = html.replace("<body>", "<body>\n  " + BANNER, 1)
    assert "{{" not in html and "{%" not in html, "unrendered template tags"
    (out / "index.html").write_text(html)
    static = out / "static"
    static.mkdir(exist_ok=True)
    for name in ("app.css", "app.js"):
        shutil.copy(ROOT / "api/static" / name, static / name)
    shutil.copy(ROOT / "pages/demo.js", static / "demo.js")
    with open(static / "app.css", "a") as css:
        css.write("\n.demo-banner { position: sticky; top: 0; z-index: 10; text-align: center; font-size: .72rem;"
                  " letter-spacing: .14em; padding: 8px; color: #04121a;"
                  " background: linear-gradient(90deg, #22d3ee, #8b5cf6); }\n")
    (out / ".nojekyll").write_text("")


if __name__ == "__main__":
    build(Path(sys.argv[1] if len(sys.argv) > 1 else "site"))
