# Git hooks

Activated with `git config core.hooksPath .githooks` (run once per clone).

## pre-commit

Runs on `git commit`, only on staged `.nix` files:

- **nixfmt** — auto-formats and re-stages
- **statix** — warns on antipatterns (doesn't block)
- **deadnix** — warns on unused bindings (doesn't block)

Bypass with `git commit --no-verify` if needed.
