import json
import os

DEFAULTS: dict = {
    "primary_color": "#3b82f6",
    "brand_name": "",
    "brand_icon": "",
}


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
