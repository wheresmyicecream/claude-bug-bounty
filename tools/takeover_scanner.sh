#!/bin/bash
# =============================================================================
# Subdomain Takeover Scanner — wrap dnsReaper / subjack with sane defaults
#
# Reference for fingerprints:
#   https://github.com/EdOverflow/can-i-take-over-xyz
#
# Usage:
#   ./tools/takeover_scanner.sh <subdomains-file>
#   ./tools/takeover_scanner.sh --recon <recon-dir>     # uses recon/<t>/subdomains/all.txt
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/external_arsenal.sh"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; MAG='\033[0;35m'; NC='\033[0m'
log()  { echo -e "${CYAN}[*]${NC} $1"; }
ok()   { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
hit()  { echo -e "${MAG}[TAKEOVER]${NC} $1"; }
err()  { echo -e "${RED}[-]${NC} $1" >&2; }

INPUT=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --recon) shift; INPUT="${1:-}/subdomains/all.txt" ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) INPUT="$1" ;;
  esac
  shift
done

[ -z "$INPUT" ] || [ ! -s "$INPUT" ] && { err "subdomains file required and non-empty"; exit 2; }

OUT_DIR="${TAKEOVER_OUT_DIR:-$(pwd)/findings/takeover/$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUT_DIR"

# shellcheck source=banner.sh
. "$SCRIPT_DIR/banner.sh"
print_banner "Subdomain Takeover Scanner" "$INPUT" \
    "dnsReaper|broad fingerprint set, JSON candidates" \
    "subjack|fast Go fallback scanner" \
    "Verify|CNAME chain + service signature match"

# Strategy 1: dnsReaper (best signal, broadest fingerprint set)
if _have dnsreaper; then
  log "dnsReaper on $(wc -l < "$INPUT" | tr -d ' ') subdomains..."
  dnsreaper file --file "$INPUT" --out "$OUT_DIR/dnsreaper.json" --out-format json 2>/dev/null || true
  if [ -s "$OUT_DIR/dnsreaper.json" ]; then
    n=$(python3 -c "import json; d=json.load(open('$OUT_DIR/dnsreaper.json')); print(len(d))" 2>/dev/null || echo 0)
    [ "$n" -gt 0 ] && hit "dnsReaper: $n candidate(s)" || ok "dnsReaper: clean"
  fi
fi

# Strategy 2: subjack (fast Go scanner, good fallback)
if _have subjack; then
  log "subjack on $(wc -l < "$INPUT" | tr -d ' ') subdomains..."
  subjack -w "$INPUT" -t 20 -ssl -o "$OUT_DIR/subjack.txt" 2>/dev/null || true
  if [ -s "$OUT_DIR/subjack.txt" ]; then
    # BUG FIX (was checking for a literal "[Vulnerable]" label that this
    # subjack version never prints -- see output.go's printResult(): a
    # candidate line is "[SERVICE_NAME] host" (e.g. "[GITHUB] foo.example.com",
    # "[DOMAIN AVAILABLE - x.com] host"), and a clean host is
    # "[Not Vulnerable] host". The old `grep -c '^\[Vulnerable\]'` matched
    # NEITHER format and silently always printed "clean" regardless of what
    # subjack actually found. Fixed by counting everything that ISN'T the
    # "[Not Vulnerable]" line.
    #
    # NOTE: subjack's live-host fingerprint match (identify() in
    # fingerprint.go) only checks whether the HTTP response body CONTAINS a
    # generic string (e.g. "page not found") -- it does NOT verify the CNAME
    # actually points to the claimed third-party service. This produces real
    # false positives (seen in practice: Xiaomi/Eternal hosts on their own
    # infra flagged as "[UPTIMEROBOT]"/"[GEMFURY]" for having an ordinary
    # 404 page). ALWAYS verify the actual CNAME before treating a hit as a
    # real candidate -- see findings/*/TEMPLATE.md 7-Question Gate.
    n=$(grep -vc '^\[Not Vulnerable\]' "$OUT_DIR/subjack.txt" 2>/dev/null || echo 0)
    if [ "$n" -gt 0 ]; then
      hit "subjack: $n candidate(s) -- cross-checking CNAME against fingerprint DB..."
      python3 "$SCRIPT_DIR/verify_takeover_candidates.py" "$OUT_DIR/subjack.txt" 2>/dev/null \
        | tee "$OUT_DIR/subjack_verified.txt"
      if grep -qE '^\[(LIKELY REAL|CONFIRM/CLAIM)\]' "$OUT_DIR/subjack_verified.txt" 2>/dev/null; then
        hit "subjack: genuine candidate(s) survived CNAME cross-check -- see $OUT_DIR/subjack_verified.txt"
      else
        ok "subjack: all $n candidate(s) were fingerprint false positives after CNAME verification"
      fi
    else
      ok "subjack: clean"
    fi
  fi
fi

# Last-resort fingerprint-grep fallback when no scanner is installed
if ! _have dnsreaper && ! _have subjack; then
  warn "No takeover scanner installed — running curl-based fingerprint grep (low signal)"
  : > "$OUT_DIR/fingerprint_grep.txt"
  # Just a handful of the most common fingerprints — extend as needed.
  while IFS= read -r host; do
    [ -z "$host" ] && continue
    body=$(curl -sk --max-time 5 "https://$host" 2>/dev/null || true)
    case "$body" in
      *"There isn't a GitHub Pages site here"*)        echo "$host  github" >> "$OUT_DIR/fingerprint_grep.txt" ;;
      *"NoSuchBucket"*)                                 echo "$host  s3"     >> "$OUT_DIR/fingerprint_grep.txt" ;;
      *"Heroku | No such app"*)                         echo "$host  heroku" >> "$OUT_DIR/fingerprint_grep.txt" ;;
      *"The specified bucket does not exist"*)          echo "$host  s3"     >> "$OUT_DIR/fingerprint_grep.txt" ;;
      *"Sorry, this shop is currently unavailable"*)    echo "$host  shopify">> "$OUT_DIR/fingerprint_grep.txt" ;;
      *"project not found"*)                            echo "$host  surge"  >> "$OUT_DIR/fingerprint_grep.txt" ;;
      *"You're Almost There"*)                          echo "$host  pantheon">> "$OUT_DIR/fingerprint_grep.txt" ;;
      *"Do you want to register"*".wordpress.com"*)     echo "$host  wpcom"  >> "$OUT_DIR/fingerprint_grep.txt" ;;
    esac
  done < "$INPUT"
  n=$(wc -l < "$OUT_DIR/fingerprint_grep.txt" | tr -d ' ')
  [ "$n" -gt 0 ] && hit "fingerprint grep: $n candidate(s)" || ok "fingerprint grep: clean"
fi

ok "Done. Output → $OUT_DIR/"
echo "Reference: https://github.com/EdOverflow/can-i-take-over-xyz for claim instructions"
