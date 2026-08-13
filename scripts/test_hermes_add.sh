#!/usr/bin/env bash
# Regression tests for scripts/hermes_add.py — the Hermes MCP registrar.
# Runs against throwaway copies of the real config; never touches ~/.hermes.
set -u

HV="${HERMES_PYTHON:-/Users/acoletti/.hermes/hermes-agent/venv/bin/python}"
[ -x "$HV" ] || HV=python3
SCRIPT="$(cd "$(dirname "$0")" && pwd)/hermes_add.py"
REAL="$HOME/.hermes/config.yaml"
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

pass=0; fail=0
check() { if [ "$2" = "$3" ]; then echo "  ok   $1"; pass=$((pass+1)); else echo "  FAIL $1 (got '$2' want '$3')"; fail=$((fail+1)); fi; }

if [ ! -f "$REAL" ]; then echo "no ~/.hermes/config.yaml — skipping"; exit 0; fi

C="$T/config.yaml"; cp "$REAL" "$C"

echo "hermes_add.py regression tests"

# 1. dry-run writes nothing
before=$(md5 -q "$C" 2>/dev/null || md5sum "$C" | cut -d' ' -f1)
"$HV" "$SCRIPT" --config "$C" --name t1 --command /x/l.sh --dry-run >/dev/null
after=$(md5 -q "$C" 2>/dev/null || md5sum "$C" | cut -d' ' -f1)
check "dry-run does not write" "$after" "$before"

# 2. add touches ONLY the new lines (the whole point of the splice approach)
"$HV" "$SCRIPT" --config "$C" --name t1 --command /x/l.sh >/dev/null
removed=$(diff "$REAL" "$C" | grep -c '^<')
check "add removes no existing lines" "$removed" "0"

# 3. add+remove is byte-identical to the original
"$HV" "$SCRIPT" --config "$C" --name t1 --remove >/dev/null
if diff -q "$REAL" "$C" >/dev/null; then r=same; else r=differs; fi
check "add+remove round-trip is lossless" "$r" "same"

# 4. idempotent add
"$HV" "$SCRIPT" --config "$C" --name t1 --command /x/l.sh >/dev/null
out=$("$HV" "$SCRIPT" --config "$C" --name t1 --command /x/l.sh)
case "$out" in *unchanged*) r=unchanged ;; *) r="$out" ;; esac
check "re-add reports unchanged" "$r" "unchanged"

# 5. update rewrites in place
"$HV" "$SCRIPT" --config "$C" --name t1 --command /y/l.sh --arg mcp >/dev/null
got=$("$HV" -c "import yaml,sys; d=yaml.safe_load(open('$C')); e=d['mcp_servers']['t1']; print(e['command'], ','.join(e.get('args',[])))")
check "update replaces command+args" "$got" "/y/l.sh mcp"

# 6. pre-existing servers survive
got=$("$HV" -c "import yaml; d=yaml.safe_load(open('$C')); print('scout' in d['mcp_servers'])")
check "existing servers preserved" "$got" "True"

# 7. env pairs land correctly
"$HV" "$SCRIPT" --config "$C" --name t2 --command /z --env A=1 --env B=2 >/dev/null
got=$("$HV" -c "import yaml; d=yaml.safe_load(open('$C')); print(d['mcp_servers']['t2']['env'])")
check "env KEY=VALUE parsed" "$got" "{'A': '1', 'B': '2'}"

# 8. malformed env rejected nonzero
"$HV" "$SCRIPT" --config "$C" --name t3 --command /z --env BAD >/dev/null 2>&1
check "malformed --env exits nonzero" "$?" "1"

# 9. missing config is a graceful skip, not a failure
"$HV" "$SCRIPT" --config "$T/nope.yaml" --name t --command /z >/dev/null 2>&1
check "missing config exits 0" "$?" "0"

# 10. remove of absent entry is a no-op
out=$("$HV" "$SCRIPT" --config "$C" --name never-existed --remove)
case "$out" in *"nothing to do"*) r=noop ;; *) r="$out" ;; esac
check "remove absent entry is a no-op" "$r" "noop"

# 11. creates mcp_servers block when absent
printf 'model: x\nother: y\n' > "$T/bare.yaml"
"$HV" "$SCRIPT" --config "$T/bare.yaml" --name t --command /z >/dev/null
got=$("$HV" -c "import yaml; d=yaml.safe_load(open('$T/bare.yaml')); print(d['mcp_servers']['t']['command'], d['model'])")
check "creates mcp_servers when absent" "$got" "/z x"

# 12. result always re-parses as valid YAML
got=$("$HV" -c "import yaml; yaml.safe_load(open('$C')); print('valid')")
check "output is parseable YAML" "$got" "valid"

echo ""
echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ]
