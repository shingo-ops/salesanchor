#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -gt 0 ]; then
  files=("$@")
else
  files=(
    "docs/STANDARD-WORKFLOW.md"
    "docs/specs/design-partner-loop/README.md"
  )
fi

overall_status=0

check_file() {
  local file="$1"

  if [ ! -f "$file" ]; then
    printf '❌ %s: file not found\n' "$file"
    overall_status=1
    return
  fi

  local heading_lines
  heading_lines="$(grep -nE '^[[:space:]]*#{2,6}[[:space:]]+[0-9]+(\.[0-9]+)*[[:space:]]' "$file" || true)"

  if [ -z "$heading_lines" ]; then
    printf '✅ %s: no duplicate canonical heading numbers\n' "$file"
    return
  fi

  local duplicate_found=0
  local seen_numbers=$'\n'
  local first_lines=$'\n'
  local line_no heading num first_line

  while IFS= read -r heading; do
    [ -n "$heading" ] || continue
    line_no="${heading%%:*}"
    heading="${heading#*:}"
    num="$(printf '%s' "$heading" | sed -E 's/^[[:space:]]*#{2,6}[[:space:]]+([0-9]+(\.[0-9]+)*).*/\1/')"

    case "$seen_numbers" in
      *$'\n'"$num"$'\n'*)
        first_line="$(printf '%s' "$first_lines" | sed -n -E "s/^${num}:([0-9]+)$/\\1/p" | head -n1)"
        printf '❌ %s: duplicate heading number %s at lines %s and %s\n' "$file" "$num" "$first_line" "$line_no"
        duplicate_found=1
        ;;
      *)
        seen_numbers+="$num"$'\n'
        first_lines+="$num:$line_no"$'\n'
        ;;
    esac
  done <<EOF
$heading_lines
EOF

  if [ "$duplicate_found" -eq 0 ]; then
    printf '✅ %s: no duplicate canonical heading numbers\n' "$file"
  else
    overall_status=1
  fi
}

for file in "${files[@]}"; do
  check_file "$file"
done

exit "$overall_status"
