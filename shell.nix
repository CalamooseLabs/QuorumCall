{pkgs}:
pkgs.mkShell {
  packages = [
    pkgs.claude-code
    (pkgs.python3.withPackages (ps: [
      ps.fastapi
      ps.uvicorn
      ps."python-multipart"
      ps.rich
      ps.pytest
      ps."pytest-cov"
      ps."pytest-sugar"
      ps.httpx
    ]))
    (pkgs.writeShellScriptBin "quorumcall" ''
      exec python3 -m cli "$@"
    '')
    (pkgs.writeShellScriptBin "runserver" ''
      exec quorumcall serve \
        --host "''${QUORUMCALL_HOST:-127.0.0.1}" \
        --port "''${QUORUMCALL_PORT:-8000}" \
        --data-dir "''${QUORUMCALL_DATA_DIR:-./data}" \
        "$@"
    '')
    (pkgs.writeShellScriptBin "runtests" ''
      exec pytest --cov=src --cov-report=term-missing "$@"
    '')
    (pkgs.writeShellScriptBin "gcommit" ''
      set -euo pipefail
      MSG_FILE="''${1:-GIT_COMMIT_MSG}"
      cat "$MSG_FILE"
      read -r -p "Proceed with signed commit? [y/N] " c
      [[ "''${c,,}" == "y" ]] && git commit -S -F "$MSG_FILE" || echo "Aborted."
    '')
  ];

  shellHook = ''
    export PYTHONPATH="$PWD/src''${PYTHONPATH:+:$PYTHONPATH}"
    echo "QuorumCall dev shell"
    echo "  quorumcall  — CLI (serve / add-poll / list-polls / expire-poll)"
    echo "  runserver   — start the polling server (./data/quorumcall.db)"
    echo "  runtests    — run test suite with branch coverage"
    echo "  gcommit     — review and sign-commit GIT_COMMIT_MSG"
  '';
}
