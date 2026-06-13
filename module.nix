# NixOS module for QuorumCall.
#
# Imported by the flake as `nixosModules.default = import ./module.nix;` and
# usable standalone (`imports = [ /path/to/module.nix ];`). The package defaults
# to `pkgs.callPackage ./build.nix {}`, so there is no dependency on flake `self`.
{ config, lib, pkgs, ... }:
let
  cfg = config.services.quorumcall;

  effectiveUser  = if cfg.runAsRoot then "root" else cfg.user;
  effectiveGroup = if cfg.runAsRoot then "root" else cfg.group;

  # Root can bind any port already. An unprivileged user needs
  # CAP_NET_BIND_SERVICE to bind a privileged (1-1023) port; port 0 asks the
  # kernel for an ephemeral (unprivileged) port, so it does not.
  needsNetBind = !cfg.runAsRoot && cfg.port > 0 && cfg.port < 1024;

  # Branding/theme settings handed to the app as a JSON file in the store.
  settingsFile = pkgs.writeText "quorumcall-settings.json" (builtins.toJSON {
    primary_color = cfg.primaryColor;
    brand_name    = cfg.brandName;
    brand_icon    = cfg.brandIcon;
  });
in
{
  options.services.quorumcall = {
    enable = lib.mkEnableOption "QuorumCall polling server";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.callPackage ./build.nix {};
      defaultText = lib.literalExpression "pkgs.callPackage ./build.nix {}";
      description = "The QuorumCall package to run.";
    };

    host = lib.mkOption {
      type = lib.types.str;
      default = "127.0.0.1";
      example = "0.0.0.0";
      description = "Host to bind to.";
    };

    port = lib.mkOption {
      type = lib.types.port;
      default = 8000;
      example = 80;
      description = ''
        Port to listen on.

        Privileged ports (1-1023, such as 80) work out of the box. When
        {option}`runAsRoot` is false — the default — the service runs as the
        unprivileged {option}`user` but is granted the `CAP_NET_BIND_SERVICE`
        capability so it can bind them.
      '';
    };

    user = lib.mkOption {
      type = lib.types.str;
      default = "quorumcall";
      description = "User account under which QuorumCall runs. Ignored when {option}`runAsRoot` is true.";
    };

    group = lib.mkOption {
      type = lib.types.str;
      default = "quorumcall";
      description = "Group under which QuorumCall runs. Ignored when {option}`runAsRoot` is true.";
    };

    runAsRoot = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = ''
        Run the service as `root` instead of the dedicated {option}`user`.

        Prefer leaving this false: the dedicated, hardened service user is more
        secure and privileged ports already work without it (see
        {option}`port`). Enable it only if you specifically need the process to
        run as root.
      '';
    };

    openFirewall = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = ''
        Whether to open {option}`port` in the firewall. Only has an effect when
        {option}`host` is reachable off-box; for the default loopback bind
        (`127.0.0.1`) the firewall is not involved.
      '';
    };

    dataDir = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/quorumcall";
      description = ''
        Directory for `quorumcall.db`, managed as a systemd `StateDirectory`.
        The service runs from this directory.
      '';
    };

    baseUrl = lib.mkOption {
      type = lib.types.str;
      default = "http://${cfg.host}:${toString cfg.port}";
      defaultText = lib.literalExpression ''"http://''${cfg.host}:''${toString cfg.port}"'';
      example = "https://polls.example.com";
      description = "Public base URL included in poll share links.";
    };

    adminKey = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "s3cr3t";
      description = ''
        Admin secret as a literal string, exported to the service as the
        QUORUMCALL_ADMIN_KEY environment variable.

        WARNING: this value is embedded in the systemd unit and is therefore
        world-readable in the Nix store. For real deployments prefer
        {option}`services.quorumcall.adminKeyFile`, which keeps the secret out
        of the store. Mutually exclusive with `adminKeyFile`.
      '';
    };

    adminKeyFile = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      example = "/run/secrets/quorumcall-admin-key";
      description = ''
        Path to an EnvironmentFile (e.g. from agenix/sops-nix or any secrets
        manager) containing QUORUMCALL_ADMIN_KEY=<secret>. Read at service
        start, so the secret never enters the Nix store. Mutually exclusive with
        `adminKey`.

        If both `adminKey` and `adminKeyFile` are null, admin routes are
        unprotected.
      '';
    };

    primaryColor = lib.mkOption {
      type = lib.types.str;
      default = "#3b82f6";
      description = "Primary accent colour (any valid CSS colour string).";
    };

    brandName = lib.mkOption {
      type = lib.types.str;
      default = "";
      description = "Organisation or brand name shown at the top of polls. Leave empty to hide.";
    };

    brandIcon = lib.mkOption {
      type = lib.types.str;
      default = "";
      description = "URL or data URI for a brand logo shown at the top of polls. Leave empty to hide.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = !(cfg.adminKey != null && cfg.adminKeyFile != null);
        message = "services.quorumcall: set at most one of `adminKey` or `adminKeyFile`, not both.";
      }
      {
        # StateDirectory must be a path relative to /var/lib, so dataDir has to live there.
        assertion = lib.hasPrefix "/var/lib/" cfg.dataDir;
        message = "services.quorumcall: dataDir must start with /var/lib/ (it is managed as a systemd StateDirectory); got ${cfg.dataDir}.";
      }
    ];

    warnings = lib.optional (cfg.adminKey != null) (
      "services.quorumcall.adminKey is written world-readable into the Nix store and shown by "
      + "`systemctl show`. Use adminKeyFile (agenix/sops-nix/an EnvironmentFile) for real secrets."
    );

    # Expose the CLI on the host so polls can be managed with
    # `quorumcall add-poll` / `list-polls` / `expire-poll`.
    environment.systemPackages = [ cfg.package ];

    networking.firewall.allowedTCPPorts = lib.mkIf cfg.openFirewall [ cfg.port ];

    users.users = lib.mkIf (!cfg.runAsRoot) {
      ${cfg.user} = {
        isSystemUser = true;
        group = cfg.group;
        description = "QuorumCall service user";
      };
    };
    users.groups = lib.mkIf (!cfg.runAsRoot) {
      ${cfg.group} = {};
    };

    # Clear any prior failed/rate-limited state before switch-to-configuration
    # tries to restart the unit, so config changes always take effect.
    system.activationScripts.quorumcall-reset-failed = lib.stringAfter [ "users" ] ''
      systemctl reset-failed quorumcall.service 2>/dev/null || true
    '';

    systemd.services.quorumcall = {
      description = "QuorumCall polling server";
      wantedBy = [ "multi-user.target" ];
      after = [ "network.target" ];

      restartTriggers = [ cfg.package cfg.host (toString cfg.port) cfg.baseUrl settingsFile ];

      environment = {
        QUORUMCALL_HOST          = cfg.host;
        QUORUMCALL_PORT          = toString cfg.port;
        QUORUMCALL_DATA_DIR      = cfg.dataDir;
        QUORUMCALL_BASE_URL      = cfg.baseUrl;
        QUORUMCALL_SETTINGS_FILE = "${settingsFile}";
        PYTHONUNBUFFERED         = "1";
      } // lib.optionalAttrs (cfg.adminKey != null) {
        QUORUMCALL_ADMIN_KEY = cfg.adminKey;
      };

      serviceConfig = {
        ExecStart = lib.concatStringsSep " " [
          "${cfg.package}/bin/quorumcall" "serve"
          "--host" cfg.host
          "--port" (toString cfg.port)
        ];

        User  = effectiveUser;
        Group = effectiveGroup;
        WorkingDirectory   = cfg.dataDir;
        StateDirectory     = lib.removePrefix "/var/lib/" cfg.dataDir;
        StateDirectoryMode = "0750";

        Restart               = "on-failure";
        RestartSec            = "5s";
        StartLimitIntervalSec = "0";

        # Hardening (applies in every mode, including runAsRoot).
        PrivateTmp     = true;
        ProtectSystem  = "strict";
        ProtectHome    = true;
        ReadWritePaths = [ cfg.dataDir ];
      }
      # Privileged port as an unprivileged user: grant just the bind capability
      # and lock the bounding set to it. (A static user does not get
      # NoNewPrivileges for free, so the bounding set is meaningful here.)
      // lib.optionalAttrs needsNetBind {
        AmbientCapabilities   = "CAP_NET_BIND_SERVICE";
        CapabilityBoundingSet = "CAP_NET_BIND_SERVICE";
      }
      # Unprivileged user not binding a privileged port: no caps needed, so
      # forbid privilege escalation outright.
      // lib.optionalAttrs (!cfg.runAsRoot && !needsNetBind) {
        NoNewPrivileges = true;
      }
      // lib.optionalAttrs (cfg.adminKeyFile != null) {
        EnvironmentFile = cfg.adminKeyFile;
      };
    };
  };
}
