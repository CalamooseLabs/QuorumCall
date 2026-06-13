# NixOS Module

QuorumCall ships a NixOS module. Add the flake as an input and enable the service:

```nix
# flake.nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    quorumcall = {
      url = "github:your-org/QuorumCall";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { nixpkgs, quorumcall, ... }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        quorumcall.nixosModules.default
        {
          services.quorumcall = {
            enable       = true;
            host         = "0.0.0.0";
            port         = 80;            # privileged ports work out of the box
            baseUrl      = "https://polls.example.com";
            adminKeyFile = "/run/secrets/quorumcall-admin-key";
          };
        }
      ];
    };
  };
}
```

By default the service runs as a dedicated, hardened **system user** (`quorumcall`).

## Module Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enable` | bool | `false` | Enable the service |
| `package` | package | flake default | Override the QuorumCall package |
| `host` | string | `"127.0.0.1"` | Bind address |
| `port` | port | `8000` | Bind port (any port, including 80/443 — see [Privileged Ports](#privileged-ports)) |
| `user` | string | `"quorumcall"` | Service user. Ignored when `runAsRoot = true` |
| `group` | string | `"quorumcall"` | Service group. Ignored when `runAsRoot = true` |
| `runAsRoot` | bool | `false` | Run as `root` instead of the dedicated user (see [Running as Root](#running-as-root)) |
| `openFirewall` | bool | `true` | Open `port` in `networking.firewall` (no effect for a loopback `host`) |
| `dataDir` | string | `"/var/lib/quorumcall"` | Database directory, managed as a systemd `StateDirectory` |
| `baseUrl` | string | `http://<host>:<port>` | Public prefix for poll share links |
| `adminKey` | null or string | `null` | Admin secret as a literal string (**insecure** — lands in the Nix store). Prefer `adminKeyFile` |
| `adminKeyFile` | null or path | `null` | Path to an EnvironmentFile holding `QUORUMCALL_ADMIN_KEY=<secret>` |
| `primaryColor` | string | `"#3b82f6"` | Accent colour (any valid CSS colour) |
| `brandName` | string | `""` | Brand name shown above polls |
| `brandIcon` | string | `""` | Brand logo URL or data URI |

## Privileged Ports

Privileged ports (1–1023, such as `80`) work without running as root. When
`port` is below 1024 and `runAsRoot` is `false`, the unit is granted
`CAP_NET_BIND_SERVICE` (via `AmbientCapabilities`, with the capability bounding
set locked to that single capability) so the unprivileged service user can bind
the port:

```nix
services.quorumcall = {
  enable = true;
  port   = 80;        # just works — no runAsRoot needed
};
```

Port `0` (an OS-assigned ephemeral port) and ports ≥ 1024 are unprivileged, so
the unit instead sets `NoNewPrivileges = true` and grants no capabilities.

## Running as Root

```nix
services.quorumcall = {
  enable    = true;
  runAsRoot = true;
};
```

`runAsRoot = true` runs the process as `root` (no dedicated user is created) and
the state directory is owned by root. Prefer leaving it `false`: the dedicated,
hardened service user is more secure, and privileged ports already work without
it. Enable it only if you specifically need the process to run as root.

## Admin Authentication

Admin routes (poll creation, listing, results, expiry) require the
`X-Admin-Key` header when a key is configured. Supply it one of two ways —
setting both is a configuration error (assertion failure):

- **`adminKeyFile`** (recommended) — a path to an EnvironmentFile containing
  `QUORUMCALL_ADMIN_KEY=<secret>`. Read at service start, so the secret never
  enters the Nix store. Composes with agenix, sops-nix, or any tool that drops a
  file on the host:

  ```nix
  services.quorumcall.adminKeyFile = config.age.secrets.quorumcall-admin.path;
  ```

- **`adminKey`** — the secret as a literal string. **Insecure**: the value is
  written world-readable into the Nix store and shown by `systemctl show`. The
  module emits a build-time warning when it is used. Reserve it for throwaway or
  local testing.

If neither is set, admin routes are unprotected.

## Branding

Set branding declaratively instead of writing a `settings.json`:

```nix
services.quorumcall = {
  enable       = true;
  primaryColor = "#0f766e";
  brandName    = "Acme Corp";
  brandIcon    = "https://example.com/logo.png";
};
```

The module writes these to a settings file in the Nix store and points the
service at it via `QUORUMCALL_SETTINGS_FILE`. See
[Configuration](configuration.md#branding-and-theming) for the field reference.

## Security Hardening

By default the service runs as a dedicated system user. The hardening applies in
every mode — when `runAsRoot` is true the process runs as root but is still
governed by the same directives:

- `ProtectSystem = strict` with `ReadWritePaths = [ dataDir ]`
- `ProtectHome = true`
- `PrivateTmp = true`
- `NoNewPrivileges = true` (when not binding a privileged port)

When `port < 1024` the unit grants `CAP_NET_BIND_SERVICE` and locks the
capability bounding set to it, so the process can bind the privileged port
without root and without being able to acquire any other capability. The
database is written to `dataDir`, managed by systemd's `StateDirectory`.

## Managing Polls on a NixOS Host

The module puts the `quorumcall` CLI on the system `PATH`
(`environment.systemPackages`). Run poll-management commands as the **service
user** so the files it creates stay owned by the service:

```bash
sudo -u quorumcall env QUORUMCALL_DATA_DIR=/var/lib/quorumcall \
  quorumcall add-poll --title "Town hall" --file poll.json

sudo -u quorumcall env QUORUMCALL_DATA_DIR=/var/lib/quorumcall \
  quorumcall list-polls
```

(When `runAsRoot = true`, run the commands as `root` instead.) See the
[CLI reference](install.md#cli) for all subcommands.

## Restart Behaviour

The unit restarts automatically on failure with a 5-second delay
(`Restart = on-failure`, `RestartSec = 5s`). Deploying a new version or changing
`host` / `port` / `baseUrl` / branding restarts the service automatically
(`restartTriggers`), and any prior failed state is cleared on activation.

```bash
# Inspect what went wrong
journalctl -u quorumcall -n 50

# Clear failure state and try again
systemctl reset-failed quorumcall
systemctl start quorumcall
```
