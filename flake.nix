{
  description = "QuorumCall — internal polling server";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = {self, nixpkgs, ...}: let
    system = "x86_64-linux";
    pkgs = import nixpkgs {
      inherit system;
      config.allowUnfree = true;
    };
    py = pkgs.python3.pkgs;

    quorumcall = py.buildPythonApplication {
      pname = "quorumcall";
      version = "0.1.0";
      src = ./.;
      pyproject = true;

      build-system = [ py.setuptools ];

      dependencies = [
        py.fastapi
        py.uvicorn
        py."python-multipart"
        py.rich
      ];
    };
  in {
    packages.${system} = {
      default = quorumcall;
      quorumcall = quorumcall;
    };

    apps.${system}.default = {
      type = "app";
      program = "${quorumcall}/bin/quorumcall";
    };

    devShells.${system}.default = import ./shell.nix {inherit pkgs;};

    nixosModules.default = {config, lib, pkgs, ...}:
      let
        cfg = config.services.quorumcall;
        pkg = self.packages.${pkgs.stdenv.hostPlatform.system}.quorumcall;
      in {
        options.services.quorumcall = {
          enable = lib.mkEnableOption "QuorumCall polling server";

          host = lib.mkOption {
            type = lib.types.str;
            default = "127.0.0.1";
            description = "Host to bind to.";
          };

          port = lib.mkOption {
            type = lib.types.int;
            default = 8000;
            description = "Port to listen on.";
          };

          dataDir = lib.mkOption {
            type = lib.types.str;
            default = "/var/lib/quorumcall";
            description = "Directory for quorumcall.db.";
          };

          baseUrl = lib.mkOption {
            type = lib.types.str;
            default = "http://localhost:8000";
            description = "Public base URL included in poll share links.";
          };

          adminKeyFile = lib.mkOption {
            type = lib.types.nullOr lib.types.path;
            default = null;
            description = ''
              Path to an EnvironmentFile containing QUORUMCALL_ADMIN_KEY=<secret>.
              If null, admin routes are unprotected.
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

        config = lib.mkIf cfg.enable (
          let
            settingsFile = pkgs.writeText "quorumcall-settings.json" (builtins.toJSON {
              primary_color = cfg.primaryColor;
              brand_name    = cfg.brandName;
              brand_icon    = cfg.brandIcon;
            });
          in {
            systemd.services.quorumcall = {
              description = "QuorumCall polling server";
              wantedBy = [ "multi-user.target" ];
              after = [ "network.target" ];

              environment = {
                QUORUMCALL_HOST         = cfg.host;
                QUORUMCALL_PORT         = toString cfg.port;
                QUORUMCALL_DATA_DIR     = cfg.dataDir;
                QUORUMCALL_BASE_URL     = cfg.baseUrl;
                QUORUMCALL_SETTINGS_FILE = "${settingsFile}";
              };

              serviceConfig = {
                ExecStart    = "${pkg}/bin/quorumcall serve";
                DynamicUser  = true;
                StateDirectory = "quorumcall";
                Restart      = "on-failure";
              } // lib.optionalAttrs (cfg.adminKeyFile != null) {
                EnvironmentFile = cfg.adminKeyFile;
              };
            };
          }
        );
      };
  };
}
