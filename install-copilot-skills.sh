#!/bin/sh
set -eu

usage() {
  cat <<'EOF'
Usage:
  ./install-copilot-skills.sh [--y]
  ./install-copilot-skills.sh --skill <skill-name> [--y]

Installs skill folders into $HOME/.copilot/skills.
Use --y to overwrite existing installed skills without prompting.
EOF
}

say() {
  printf '%s\n' "$*"
}

prompt_yes_no() {
  prompt="$1"
  printf '%s [y/N] ' "$prompt"
  IFS= read -r answer || answer=""
  case "$answer" in
    y|Y|yes|YES|Yes) return 0 ;;
    *) return 1 ;;
  esac
}

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET_DIR="$HOME/.copilot/skills"
SKILL_NAME=""
AUTO_OVERWRITE=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --skill)
      if [ "$#" -lt 2 ] || [ -z "$2" ]; then
        usage
        exit 1
      fi
      SKILL_NAME="$2"
      shift 2
      ;;
    --y)
      AUTO_OVERWRITE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      say "Unsupported option: $1"
      usage
      exit 1
      ;;
  esac
done

check_latest_version() {
  if ! command -v git >/dev/null 2>&1; then
    say "Note: git is not available, so automatic latest-version checking is unavailable."
    return
  fi

  if ! git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    say "Note: automatic latest-version checking is unavailable because this folder is not a Git repository."
    return
  fi

  upstream=$(git -C "$SCRIPT_DIR" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)
  if [ -z "$upstream" ]; then
    say "Note: automatic latest-version checking is unavailable because no upstream remote is configured."
    return
  fi

  if ! git -C "$SCRIPT_DIR" fetch --quiet; then
    say "Warning: failed to fetch remote metadata. Continuing with the current local version."
    return
  fi

  local_head=$(git -C "$SCRIPT_DIR" rev-parse HEAD)
  upstream_head=$(git -C "$SCRIPT_DIR" rev-parse "$upstream")
  merge_base=$(git -C "$SCRIPT_DIR" merge-base HEAD "$upstream")

  if [ "$local_head" = "$upstream_head" ]; then
    say "Local skills are up to date."
  elif [ "$merge_base" = "$local_head" ]; then
    if prompt_yes_no "Local skills are not the latest version. Update before installing?"; then
      if ! git -C "$SCRIPT_DIR" pull --ff-only; then
        say "Error: git pull --ff-only failed. Stop installing."
        exit 1
      fi
    else
      say "Continuing with the current local version."
    fi
  else
    say "Warning: local skills differ from upstream. Continuing with the current local version."
  fi
}

skill_has_manifest() {
  [ -d "$1" ] && [ -f "$1/SKILL.md" ]
}

copy_skill_dir() {
  src="$1"
  dest="$2"
  mkdir -p "$dest"

  (
    cd "$src"
    find . \( -name node_modules -o -name .DS_Store \) -prune -o -type d -print
  ) | while IFS= read -r dir_path; do
    mkdir -p "$dest/$dir_path"
  done

  (
    cd "$src"
    find . \( -name node_modules -o -name .DS_Store \) -prune -o -type f -print
  ) | while IFS= read -r file_path; do
    parent=$(dirname -- "$file_path")
    mkdir -p "$dest/$parent"
    cp -p "$src/$file_path" "$dest/$file_path"
  done
}

install_skill() {
  name="$1"
  src="$SCRIPT_DIR/$name"
  dest="$TARGET_DIR/$name"

  if ! skill_has_manifest "$src"; then
    say "Error: requested skill \"$name\" does not exist or lacks SKILL.md."
    exit 1
  fi

  if [ -e "$dest" ]; then
    if [ "$AUTO_OVERWRITE" -eq 1 ] || prompt_yes_no "Skill \"$name\" already exists in target. Overwrite?"; then
      timestamp=$(date +%Y%m%d-%H%M%S)
      backup_dir="$TARGET_DIR/.backup"
      backup_path="$backup_dir/$name-$timestamp"
      mkdir -p "$backup_dir"
      if [ -e "$backup_path" ]; then
        backup_path="$backup_path-$$"
      fi
      mv "$dest" "$backup_path"
      say "Backed up existing \"$name\" to $backup_path"
    else
      say "Skipped \"$name\"."
      return
    fi
  fi

  copy_skill_dir "$src" "$dest"
  say "Installed \"$name\" to $dest"
}

install_all_skills() {
  found=0
  for candidate in "$SCRIPT_DIR"/*; do
    if skill_has_manifest "$candidate"; then
      found=1
      install_skill "$(basename -- "$candidate")"
    fi
  done

  if [ "$found" -eq 0 ]; then
    say "Error: no skill folders containing SKILL.md were found."
    exit 1
  fi
}

check_latest_version
mkdir -p "$TARGET_DIR"

if [ -n "$SKILL_NAME" ]; then
  install_skill "$SKILL_NAME"
else
  install_all_skills
fi
