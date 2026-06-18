import json
import os
import re

DEFAULTS: dict = {
    "primary_color": "#3b82f6",
    "brand_name": "",
    "brand_icon": "",
}

DEFAULT_BASE_URL = "http://localhost:8000"

# Accept only safe CSS colour syntaxes: #hex, a bare CSS identifier (named
# colours), or rgb()/rgba()/hsl()/hsla(). Anything else (e.g. a value carrying
# "</style>", "{" or ";") falls back to the default so it cannot break out of
# the inline <style> block it is injected into.
_COLOR_RE = re.compile(
    r"^#[0-9A-Fa-f]{3,8}$"
    r"|^[A-Za-z]+$"
    r"|^(?:rgb|rgba|hsl|hsla)\([0-9.,%\s/deg]+\)$"
)


def load_settings() -> dict:
    path = os.environ.get("QUORUMCALL_SETTINGS_FILE")
    if not path:
        data_dir = os.environ.get("QUORUMCALL_DATA_DIR", ".")
        path = os.path.join(data_dir, "settings.json")
    try:
        with open(path) as f:
            return {**DEFAULTS, **json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(DEFAULTS)


def base_url() -> str:
    """Public base URL used to build shareable poll links."""
    return os.environ.get("QUORUMCALL_BASE_URL", DEFAULT_BASE_URL)


def _safe_color(value: str) -> str:
    return value if isinstance(value, str) and _COLOR_RE.match(value.strip()) else DEFAULTS["primary_color"]


def inject_theme(template: str, settings: dict) -> str:
    """Inject the accent colour and brand settings into a page template.

    Shared by ui.render_html and builder.render_builder_html. The colour is
    validated against a CSS-colour allowlist, and the JSON settings have their
    ``</`` sequences neutralised so a brand value containing ``</script>`` cannot
    break out of the inline <script> block.
    """
    s = {**DEFAULTS, **settings}
    css_var = f"--p:{_safe_color(s['primary_color'])};"
    js_settings = json.dumps({
        "brand_name": s["brand_name"],
        "brand_icon": s["brand_icon"],
    }).replace("</", "<\\/")
    return (
        template
        .replace("/*__QC_THEME__*/", css_var)
        .replace('"__QC_SETTINGS__"', js_settings)
    )
