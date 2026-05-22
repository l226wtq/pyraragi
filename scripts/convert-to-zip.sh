#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/convert-to-zip.sh [options] <file-or-directory>...

Convert .rar/.cbr/.7z/.cb7 archives to ZIP-compatible archives for Pyrragi.
Directories are scanned recursively.

Options:
  -d, --dest DIR       Write converted files to DIR. Defaults to each source file's directory.
      --cbz            Use .cbz output extension instead of .zip.
      --overwrite      Replace existing output files.
      --delete-source  Delete the original archive after a successful conversion.
  -h, --help           Show this help.

Dependencies:
  zip is required.
  RAR/CBR extraction uses unrar, 7z/7zz, or unar.
  7Z/CB7 extraction uses 7z/7zz or unar.

Examples:
  scripts/convert-to-zip.sh ~/Books
  scripts/convert-to-zip.sh --cbz -d storage/archives ~/Downloads/*.rar
  scripts/convert-to-zip.sh --overwrite --delete-source ~/Books
EOF
}

log() {
  printf '[convert-to-zip] %s\n' "$*" >&2
}

fail() {
  printf '[convert-to-zip] ERROR: %s\n' "$*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

find_cmd() {
  local name
  for name in "$@"; do
    if command -v "$name" >/dev/null 2>&1; then
      printf '%s\n' "$name"
      return 0
    fi
  done
  return 1
}

is_source_archive() {
  local lower
  lower="${1,,}"
  case "$lower" in
    *.rar|*.cbr|*.7z|*.cb7) return 0 ;;
    *) return 1 ;;
  esac
}

archive_kind() {
  local lower
  lower="${1,,}"
  case "$lower" in
    *.rar|*.cbr) printf 'rar\n' ;;
    *.7z|*.cb7) printf '7z\n' ;;
    *) return 1 ;;
  esac
}

strip_archive_extension() {
  local name
  name="$(basename "$1")"
  case "${name,,}" in
    *.cbr|*.cb7|*.rar|*.7z) printf '%s\n' "${name%.*}" ;;
    *) printf '%s\n' "$name" ;;
  esac
}

extract_archive() {
  local src="$1"
  local dest="$2"
  local kind="$3"
  local sevenz

  if [[ "$kind" == "rar" ]]; then
    if command -v unrar >/dev/null 2>&1; then
      unrar x -idq -o+ -- "$src" "$dest/" >/dev/null
      return
    fi

    sevenz="$(find_cmd 7zz 7z || true)"
    if [[ -n "$sevenz" ]]; then
      "$sevenz" x -y -bd "-o$dest" -- "$src" >/dev/null
      return
    fi

    if command -v unar >/dev/null 2>&1; then
      unar -quiet -force-overwrite -output-directory "$dest" -- "$src" >/dev/null
      return
    fi

    fail "No extractor found for RAR. Install unrar, 7zip, or unar."
  fi

  if [[ "$kind" == "7z" ]]; then
    sevenz="$(find_cmd 7zz 7z || true)"
    if [[ -n "$sevenz" ]]; then
      "$sevenz" x -y -bd "-o$dest" -- "$src" >/dev/null
      return
    fi

    if command -v unar >/dev/null 2>&1; then
      unar -quiet -force-overwrite -output-directory "$dest" -- "$src" >/dev/null
      return
    fi

    fail "No extractor found for 7Z. Install 7zip or unar."
  fi

  fail "Unsupported archive type: $src"
}

make_zip() {
  local source_dir="$1"
  local output_file="$2"
  (
    cd "$source_dir"
    zip -qr -X "$output_file" .
  )
}

collect_inputs() {
  local input
  for input in "$@"; do
    if [[ -d "$input" ]]; then
      find "$input" -type f \( -iname '*.rar' -o -iname '*.cbr' -o -iname '*.7z' -o -iname '*.cb7' \) -print0
    elif [[ -f "$input" ]] && is_source_archive "$input"; then
      printf '%s\0' "$input"
    else
      log "Skipping unsupported input: $input"
    fi
  done
}

dest_dir=""
output_ext="zip"
overwrite="false"
delete_source="false"
inputs=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -d|--dest)
      [[ $# -ge 2 ]] || fail "$1 requires a directory"
      dest_dir="$2"
      shift 2
      ;;
    --cbz)
      output_ext="cbz"
      shift
      ;;
    --overwrite)
      overwrite="true"
      shift
      ;;
    --delete-source)
      delete_source="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do
        inputs+=("$1")
        shift
      done
      ;;
    -*)
      fail "Unknown option: $1"
      ;;
    *)
      inputs+=("$1")
      shift
      ;;
  esac
done

[[ ${#inputs[@]} -gt 0 ]] || {
  usage
  exit 1
}

need_cmd zip

if [[ -n "$dest_dir" ]]; then
  mkdir -p "$dest_dir"
fi

converted=0
skipped=0
failed=0

while IFS= read -r -d '' src; do
  kind="$(archive_kind "$src")"
  base="$(strip_archive_extension "$src")"
  out_dir="${dest_dir:-$(dirname "$src")}"
  mkdir -p "$out_dir"
  out_dir="$(cd "$out_dir" && pwd -P)"
  output="$out_dir/$base.$output_ext"

  if [[ -e "$output" && "$overwrite" != "true" ]]; then
    log "Skipping existing output: $output"
    skipped=$((skipped + 1))
    continue
  fi

  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT

  log "Converting: $src -> $output"
  if extract_archive "$src" "$tmp" "$kind" && make_zip "$tmp" "$output"; then
    converted=$((converted + 1))
    if [[ "$delete_source" == "true" ]]; then
      rm -f -- "$src"
    fi
  else
    failed=$((failed + 1))
    rm -f -- "$output"
    log "Failed: $src"
  fi

  rm -rf "$tmp"
  trap - EXIT
done < <(collect_inputs "${inputs[@]}")

log "Done. converted=$converted skipped=$skipped failed=$failed"

if [[ "$failed" -gt 0 ]]; then
  exit 1
fi
