#!/usr/bin/env bash
# ideas.sh - list and filter concrete follow-up items
#
# Agents use this to inventory item metadata without loading full item bodies.
# Items live in docs/ideas/*.md with YAML frontmatter.
#
# Usage:
#   docs/ideas/ideas.sh                       list title and description for all items
#   docs/ideas/ideas.sh --details              show area, priority, trigger, source, file path
#   docs/ideas/ideas.sh --fields               show frontmatter key-value pairs for all items
#   docs/ideas/ideas.sh --check                validate item frontmatter
#   docs/ideas/ideas.sh --area protocol        filter by area
#   docs/ideas/ideas.sh --priority next-candidate  filter by priority
#   docs/ideas/ideas.sh --group area           group output by a frontmatter field
#   docs/ideas/ideas.sh --group priority       group output by priority
#   docs/ideas/ideas.sh --help                 show this help and declared fields
#
# Frontmatter fields:
#   title        (required) short actionable title
#   description  (required) one-sentence summary
#   area         (optional) category: protocol, core, adapters, pi-extension, claude-code,
#                             packaging, developer-experience, security, other
#   priority     (optional) user-prioritized | next-candidate | normal | deferred
#   trigger      (optional) what would justify promoting this into active scope
#   source       (optional) where this item originated
#
# Items are open by existence and closed by removal.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ITEMS_DIR="$SCRIPT_DIR"

die() { echo "$*" >&2; exit 1; }

fm_get() {
  local file="$1" key="$2"
  awk -v k="$key" '
    /^---$/ { fm++; next }
    fm == 1 {
      if ($0 ~ "^" k ":") {
        sub("^" k ":[[:space:]]*", "")
        print
        found = 1
        exit
      }
    }
  ' "$file"
}

fm_all() {
  awk '
    /^---$/ { fm++; next }
    fm == 1 && NF > 0 { print }
  ' "$1"
}

item_files() {
  find "$ITEMS_DIR" -maxdepth 1 -name '*.md' ! -name 'README.md' ! -name '_*.md' -type f 2>/dev/null | sort
}

item_value() {
  local file="$1" key="$2" value
  value="$(fm_get "$file" "$key")"
  if [[ "$key" == "priority" && -z "$value" ]]; then
    value="normal"
  fi
  echo "$value"
}

relpath() {
  local full="$1"
  echo "${full#"$PROJECT_DIR/"}"
}

# ── Display modes ──

show_brief() {
  local file="$1" title desc name
  title="$(fm_get "$file" title)"
  desc="$(fm_get "$file" description)"
  name="$(basename "$file")"
  printf "%s (%s)\n  - %s.\n\n" "$title" "$name" "${desc%.}"
}

show_detail() {
  local file="$1" title desc area priority trigger source
  title="$(fm_get "$file" title)"
  desc="$(fm_get "$file" description)"
  area="$(fm_get "$file" area)"
  priority="$(item_value "$file" priority)"
  trigger="$(fm_get "$file" trigger)"
  source="$(fm_get "$file" source)"
  printf "%s\n" "$title"
  printf "  Description: %s\n" "$desc"
  [[ -n "$area" ]] && printf "  Area: %s\n" "$area"
  [[ -n "$priority" ]] && printf "  Priority: %s\n" "$priority"
  [[ -n "$trigger" ]] && printf "  Trigger: %s\n" "$trigger"
  [[ -n "$source" ]] && printf "  Source: %s\n" "$source"
  printf "  File: %s\n" "$(relpath "$file")"
}

show_fields() {
  local file="$1"
  printf "%s\n" "$(relpath "$file")"
  fm_all "$file" | while IFS= read -r line; do
    printf "  %s\n" "$line"
  done
}

# ── Validation ──

check_items() {
  local failures=0 count=0 file key priority title desc
  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    count=$((count + 1))
    title="$(fm_get "$file" title)"
    desc="$(fm_get "$file" description)"
    if [[ -z "$title" ]]; then
      echo "Missing required field 'title': $(relpath "$file")" >&2
      failures=$((failures + 1))
    fi
    if [[ -z "$desc" ]]; then
      echo "Missing required field 'description': $(relpath "$file")" >&2
      failures=$((failures + 1))
    fi

    while IFS= read -r key; do
      [[ -z "$key" ]] && continue
      case "$key" in
        title|description|area|priority|trigger|source) ;;
        *)
          echo "Unknown frontmatter field '$key': $(relpath "$file")" >&2
          failures=$((failures + 1))
          ;;
      esac
    done < <(fm_all "$file" | awk -F: '/^[A-Za-z_][A-Za-z0-9_-]*:/ { print $1 }')

    priority="$(fm_get "$file" priority)"
    if [[ -n "$priority" ]]; then
      case "$priority" in
        user-prioritized|next-candidate|normal|deferred) ;;
        *)
          echo "Invalid priority '$priority': $(relpath "$file")" >&2
          failures=$((failures + 1))
          ;;
      esac
    fi
  done < <(item_files)

  if [[ "$failures" -eq 0 ]]; then
    echo "OK: $count item(s) checked."
    return 0
  fi

  echo "FAILED: $failures issue(s) found across $count item(s)." >&2
  return 1
}

# ── Filtering ──

matches_filter() {
  local file="$1"
  if [[ -n "$FILTER_AREA" ]]; then
    [[ "$(fm_get "$file" area)" == "$FILTER_AREA" ]] || return 1
  fi
  if [[ -n "$FILTER_PRIORITY" ]]; then
    [[ "$(item_value "$file" priority)" == "$FILTER_PRIORITY" ]] || return 1
  fi
  return 0
}

# ── Grouping ──

group_output() {
  local field="$1"
  local unmatched=()

  local groups_file
  groups_file="$(mktemp)"
  trap 'rm -f "$groups_file"' EXIT

  local file group_val
  for file in $(item_files); do
    matches_filter "$file" || continue
    group_val="$(item_value "$file" "$field")"
    [[ -z "$group_val" ]] && group_val="(none)"
    echo "$group_val" >> "$groups_file"
  done

  local found=0
  local g
  while IFS= read -r g; do
    [[ -z "$g" ]] && continue
    found=1
    printf "\n== %s ==\n" "$g"
    for file in $(item_files); do
      matches_filter "$file" || continue
      local gv
      gv="$(item_value "$file" "$field")"
      [[ -z "$gv" ]] && gv="(none)"
      [[ "$gv" == "$g" ]] && "show_$MODE" "$file"
    done
  done < <(sort -u "$groups_file")

  rm -f "$groups_file"
  trap - EXIT

  if [[ "$found" -eq 0 ]]; then
    echo "No items found."
  fi
}

# ── Option parsing ──

MODE=brief
FILTER_AREA=""
FILTER_PRIORITY=""
GROUP_FIELD=""

show_help() {
  cat <<'HELP'
ideas.sh - list and filter concrete follow-up items

Usage:
  docs/ideas/ideas.sh                       list title and description for all items
  docs/ideas/ideas.sh --details              show area, priority, trigger, source, file path
  docs/ideas/ideas.sh --fields               show frontmatter key-value pairs for all items
  docs/ideas/ideas.sh --check                validate item frontmatter
  docs/ideas/ideas.sh --area <area>          filter by area
  docs/ideas/ideas.sh --priority <priority>  filter by priority
  docs/ideas/ideas.sh --group <field>        group output by a frontmatter field
  docs/ideas/ideas.sh --help                 show this help

Frontmatter fields (required: title, description; optional: area, priority, trigger, source):

  title        Short actionable title for the item
  description  One-sentence summary
  area         Category: protocol, core, adapters, pi-extension, claude-code,
               packaging, developer-experience, security, other
  priority     user-prioritized | next-candidate | normal | deferred
  trigger      What would justify promoting this into active scope
  source       Where this item originated

Priority defaults to "normal" when not specified.
Items are open by existence and closed by removal.
HELP
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --details)    MODE=detail; shift;;
    --fields)     MODE=fields; shift;;
    --check)      MODE=check; shift;;
    --group)      GROUP_FIELD="$2"; shift 2;;
    --area)       FILTER_AREA="$2"; shift 2;;
    --priority)   FILTER_PRIORITY="$2"; shift 2;;
    --help|-h)    show_help; exit 0;;
    *)            die "Unknown option: $1";;
  esac
done

if [[ "$MODE" == "check" ]]; then
  check_items
  exit $?
fi

if [[ -n "$GROUP_FIELD" ]]; then
  group_output "$GROUP_FIELD"
  exit 0
fi

if [[ "$MODE" == "brief" ]]; then
  printf "Concrete follow-up items:\n\n"
fi

count=0
for file in $(item_files); do
  matches_filter "$file" || continue
  "show_$MODE" "$file"
  count=$((count + 1))
done

if [[ $count -eq 0 ]]; then
  echo "No items found."
elif [[ "$MODE" == "brief" ]]; then
  echo "Use: docs/ideas/ideas.sh --details | --group area | --priority next-candidate | --check | --help"
fi
