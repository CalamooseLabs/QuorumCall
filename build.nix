# QuorumCall package derivation.
#
# Self-contained so it can be built without the flake:
#   nix-build build.nix
# and is wired into the flake via `pkgs.callPackage ./build.nix {}`.
{ pkgs ? import <nixpkgs> {} }:

let
  py = pkgs.python3.pkgs;
  # Single source of truth for the version: read it from src/_version.py so it
  # never drifts from the Python package (pyproject derives its version there too).
  version = builtins.head (
    builtins.match "[^\"]*\"([^\"]+)\"[[:space:]]*" (builtins.readFile ./src/_version.py)
  );
in
py.buildPythonApplication {
  pname = "quorumcall";
  inherit version;
  src = ./.;
  pyproject = true;

  build-system = [ py.setuptools ];

  dependencies = [
    py.fastapi
    py.uvicorn
    py."python-multipart"
    py.rich
  ];

  # Run the (fast, non-integration) test suite at build time so a broken build
  # can't be packaged. Integration tests are excluded by the pyproject addopts.
  nativeCheckInputs = [ py.pytestCheckHook py.httpx ];
}
