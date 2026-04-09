#!/usr/bin/env bash
# Claude Code statusline: model, context usage, cost, tokens
DATA=$(cat)

PARSED=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
cw = d.get('context_window') or {}
cost = d.get('cost') or {}
m = d.get('model') or {}
print(m.get('display_name') or m.get('id') or 'unknown')
print(int(cw.get('used_percentage') or 0))
print(float(cost.get('total_cost_usd') or 0))
print(int(cw.get('total_input_tokens') or 0))
print(int(cw.get('total_output_tokens') or 0))
" "$DATA")

MODEL=$(   sed -n '1p' <<< "$PARSED")
CTX=$(     sed -n '2p' <<< "$PARSED")
COST_USD=$(sed -n '3p' <<< "$PARSED")
IN_TOK=$(  sed -n '4p' <<< "$PARSED")
OUT_TOK=$( sed -n '5p' <<< "$PARSED")

if [[ "${ANTHROPIC_BASE_URL:-}" == *"mimo"* ]]; then
  API_LABEL="MiMo"
  COST=$(python3 -c "print(f'~\${(${IN_TOK}/1000000)*1 + (${OUT_TOK}/1000000)*3:.4f}')")
else
  API_LABEL="Official"
  COST=$(python3 -c "print(f'\${${COST_USD}:.4f}')")
fi

BAR_W=10
FILLED=$(( CTX * BAR_W / 100 ))
BAR=""
for i in $(seq 1 $FILLED);             do BAR="${BAR}█"; done
for i in $(seq $((FILLED+1)) $BAR_W);  do BAR="${BAR}░"; done

if   [ "$CTX" -ge 80 ]; then C="\033[31m"
elif [ "$CTX" -ge 60 ]; then C="\033[33m"
else                          C="\033[32m"
fi
R="\033[0m"

echo -e "${C}[${BAR}] ${CTX}%${R} | ${MODEL} (${API_LABEL}) | ${COST} | in:${IN_TOK} out:${OUT_TOK}"
