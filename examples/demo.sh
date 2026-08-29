#!/usr/bin/env bash
set -euo pipefail

demo_root=$(mktemp -d)
trap 'rm -rf "$demo_root"' EXIT

mkdir -p "$demo_root/.agents"
printf '%s\n' 'Review code carefully.' > "$demo_root/.agents/reviewer.md"
cp "$(dirname "$0")/../profiles/generic.toml" "$demo_root/selfedit-policy.toml"
printf '%s\n' 'Review code carefully.' > "$demo_root/old.txt"
printf '%s\n' 'Review code and cite evidence.' > "$demo_root/new.txt"

cd "$demo_root"
selfedit-gate check .agents/reviewer.md
selfedit-gate replace .agents/reviewer.md old.txt new.txt
selfedit-gate verify-receipts

if selfedit-gate check .github/workflows/ci.yml; then
  echo "protected-path demo unexpectedly succeeded" >&2
  exit 1
fi

printf '\nFinal behaviour file:\n'
cat .agents/reviewer.md
