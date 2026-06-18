{
  description = "QuorumCall — internal polling server";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = {self, nixpkgs, ...} @ inputs: let
    system = "x86_64-linux";
    # Free package set: the package and app outputs stay free of any unfree taint.
    pkgs = import nixpkgs { inherit system; };
    # The dev shell pulls in the (unfree) claude-code editor; allow only that,
    # scoped to the shell so it never affects the package/app outputs.
    pkgsShell = import nixpkgs {
      inherit system;
      config.allowUnfreePredicate = p: builtins.elem (pkgs.lib.getName p) [ "claude-code" ];
    };
    quorumcall = pkgs.callPackage ./build.nix {};
  in {
    packages.${system} = {
      default = quorumcall;
      quorumcall = quorumcall;
    };

    apps.${system}.default = {
      type = "app";
      program = "${quorumcall}/bin/quorumcall";
    };

    devShells.${system}.default = import ./shell.nix { pkgs = pkgsShell; };

    nixosModules.default = import ./module.nix;
  };
}
