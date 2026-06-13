{
  description = "QuorumCall — internal polling server";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = {self, nixpkgs, ...} @ inputs: let
    system = "x86_64-linux";
    pkgs = import nixpkgs {
      inherit system;
      config.allowUnfree = true;
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

    devShells.${system}.default = import ./shell.nix { inherit pkgs; };

    nixosModules.default = import ./module.nix;
  };
}
