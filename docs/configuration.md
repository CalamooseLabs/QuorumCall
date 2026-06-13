# Configuration

QuorumCall is configured entirely through environment variables. CLI flags
(`--host`, `--port`, `--data-dir`) take precedence over the corresponding env
vars. On NixOS these are set for you by the [module](nixos.md).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QUORUMCALL_HOST` | `127.0.0.1` | Bind address |
| `QUORUMCALL_PORT` | `8000` | Bind port |
| `QUORUMCALL_DATA_DIR` | `.` | Directory for `quorumcall.db` |
| `QUORUMCALL_BASE_URL` | `http://localhost:8000` | Prefix for poll share links |
| `QUORUMCALL_ADMIN_KEY` | *(unset — open)* | If set, required as the `X-Admin-Key` header on admin routes |
| `QUORUMCALL_SETTINGS_FILE` | `{data_dir}/settings.json` | Path to the branding/theme settings file |

## Branding and Theming

Create a `settings.json` in the data directory (or point `QUORUMCALL_SETTINGS_FILE`
at one) to customise the poll UI:

```json
{
  "primary_color": "#0f766e",
  "brand_name": "Acme Corp",
  "brand_icon": "https://example.com/logo.png"
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `primary_color` | `#3b82f6` | Button and accent colour (any valid CSS colour) |
| `brand_name` | *(empty)* | Organisation name shown above each poll |
| `brand_icon` | *(empty)* | URL or data URI for a logo shown above each poll |

The brand bar is hidden when both `brand_name` and `brand_icon` are empty.

On NixOS, set these declaratively with the `primaryColor` / `brandName` /
`brandIcon` module options instead of writing a file — see
[NixOS Module → Branding](nixos.md#branding).
