# QuorumCall package derivation.
#
# Self-contained so it can be built without the flake:
#   nix-build build.nix
# and is wired into the flake via `pkgs.callPackage ./build.nix {}`.
{ pkgs ? import <nixpkgs> {} }:

let
  py = pkgs.python3.pkgs;
in
py.buildPythonApplication {
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
}
