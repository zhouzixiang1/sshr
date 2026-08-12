#!/usr/bin/env bash
# Synchronize the current Resource-NMCTS Chinese competition manuscript into its
# dedicated Overleaf Git worktree.  Default mode is read-only comparison.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mode="check"
overleaf_dir="${OVERLEAF_WORKTREE:-}"
commit_message="sync: update AI-Q Boolean Oracle manuscript"

usage() {
  cat <<'EOF'
Usage:
  sync_to_overleaf.sh --check|--apply|--push [--overleaf-dir PATH] [--message TEXT]

Modes:
  --check  Compare only (default); exits 1 when the selected payload differs.
  --apply  Copy selected manuscript assets and compile in a temporary output dir.
  --push   Apply, compile, commit the selected payload, and push origin/main.

By default, the script uses the project-local worktree beside this script.
Set --overleaf-dir or OVERLEAF_WORKTREE only to override that location.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) mode="check" ;;
    --apply) mode="apply" ;;
    --push) mode="push" ;;
    --overleaf-dir)
      shift
      overleaf_dir="${1:-}"
      ;;
    --message)
      shift
      commit_message="${1:-}"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ -z "$overleaf_dir" ]]; then
  overleaf_dir="$script_dir/worktree"
fi

if [[ -z "$overleaf_dir" || ! -d "$overleaf_dir/.git" ]]; then
  printf 'Expected a checked-out Overleaf Git repository at: %s\n' "$overleaf_dir" >&2
  exit 2
fi

project_dir="$(cd -- "$script_dir/.." && pwd)"
repo_root="$(cd -- "$script_dir/../../../.." && pwd)"
target_dir="$(cd -- "$overleaf_dir" && pwd)"
main_source="$project_dir/chinese/main.tex"
algorithm_source="$project_dir/chinese/algorithms/resource_nmcts_budgeted_search_zh.tex"
readme_source="$script_dir/README_OVERLEAF.md"
tables_dir="$project_dir/english/tables"
figures_dir="$project_dir/english/figures/submission_v36"
expected_project_id="6a748d57e970d09ad3c0dda4"

if [[ ! -f "$main_source" || ! -f "$algorithm_source" || ! -f "$readme_source" ]]; then
  printf '%s\n' 'Canonical manuscript, algorithm, or Overleaf README asset is missing.' >&2
  exit 2
fi

remote_url="$(git -C "$target_dir" remote get-url origin)"
if [[ "$remote_url" != *"$expected_project_id"* ]]; then
  printf 'Refusing target with unexpected origin: %s\n' "$remote_url" >&2
  exit 2
fi

transform_main() {
  sed \
    -e 's#\\graphicspath{{../english/figures/submission_v36/}}#\\graphicspath{{figures/}}#' \
    -e 's#../english/tables/#tables/#g' \
    "$main_source"
}

table_refs() {
  sed -nE 's@.*\\input\{../english/tables/([^}]*)\}.*@\1@p' "$main_source"
}

figure_refs() {
  sed -nE 's@.*\\includegraphics(\[[^]]*\])?\{([^}]*)\}.*@\2@p' "$main_source"
}

table_file() {
  local ref="$1"
  if [[ "$ref" == *.tex ]]; then
    printf '%s\n' "$ref"
  else
    printf '%s.tex\n' "$ref"
  fi
}

require_source_assets() {
  local ref file
  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    file="$(table_file "$ref")"
    [[ -f "$tables_dir/$file" ]] || { printf 'Missing table asset: %s\n' "$file" >&2; exit 2; }
  done < <(table_refs)

  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    [[ -f "$figures_dir/$ref" ]] || { printf 'Missing figure asset: %s\n' "$ref" >&2; exit 2; }
  done < <(figure_refs)
}

assert_clean_target() {
  if [[ -n "$(git -C "$target_dir" status --porcelain)" ]]; then
    printf '%s\n' 'Refusing to overwrite a dirty Overleaf worktree. Commit, stash, or resolve it first.' >&2
    git -C "$target_dir" status --short >&2
    exit 2
  fi
}

assert_only_selected_payload_changes() {
  local changed
  while IFS= read -r changed; do
    [[ -z "$changed" ]] && continue
    case "$changed" in
      main.tex|README_OVERLEAF.md|algorithms/*|tables/*|figures/*)
        ;;
      *)
        printf 'Refusing to push with unrelated local change: %s\n' "$changed" >&2
        exit 2
        ;;
    esac
  done < <(git -C "$target_dir" status --porcelain | cut -c4-)
}

compare_payload() {
  local drift=0 ref file
  if ! cmp -s "$target_dir/main.tex" <(transform_main); then
    printf '%s\n' 'DIFF main.tex'
    diff -u "$target_dir/main.tex" <(transform_main) || true
    drift=1
  fi

  if ! cmp -s "$algorithm_source" "$target_dir/algorithms/$(basename "$algorithm_source")"; then
    printf 'DIFF algorithms/%s\n' "$(basename "$algorithm_source")"
    drift=1
  fi

  if ! cmp -s "$readme_source" "$target_dir/README_OVERLEAF.md"; then
    printf '%s\n' 'DIFF README_OVERLEAF.md'
    drift=1
  fi

  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    file="$(table_file "$ref")"
    if ! cmp -s "$tables_dir/$file" "$target_dir/tables/$file"; then
      printf 'DIFF tables/%s\n' "$file"
      drift=1
    fi
  done < <(table_refs)

  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    if ! cmp -s "$figures_dir/$ref" "$target_dir/figures/$ref"; then
      printf 'DIFF figures/%s\n' "$ref"
      drift=1
    fi
  done < <(figure_refs)

  return "$drift"
}

apply_payload() {
  local ref file
  mkdir -p "$target_dir/algorithms" "$target_dir/tables" "$target_dir/figures"
  transform_main > "$target_dir/main.tex"
  cp -p "$algorithm_source" "$target_dir/algorithms/$(basename "$algorithm_source")"
  cp -p "$readme_source" "$target_dir/README_OVERLEAF.md"

  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    file="$(table_file "$ref")"
    cp -p "$tables_dir/$file" "$target_dir/tables/$file"
  done < <(table_refs)

  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    cp -p "$figures_dir/$ref" "$target_dir/figures/$ref"
  done < <(figure_refs)
}

stage_payload() {
  local ref file
  git -C "$target_dir" add -- main.tex README_OVERLEAF.md "algorithms/$(basename "$algorithm_source")"
  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    file="$(table_file "$ref")"
    git -C "$target_dir" add -- "tables/$file"
  done < <(table_refs)
  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    git -C "$target_dir" add -- "figures/$ref"
  done < <(figure_refs)
}

compile_target() {
  local build_dir
  build_dir="$(mktemp -d "${TMPDIR:-/tmp}/resource-nmcts-overleaf-build.XXXXXX")"
  (
    cd "$target_dir"
    latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir="$build_dir" main.tex
  )
  printf 'Compiled PDF: %s/main.pdf\n' "$build_dir"
}

require_source_assets

case "$mode" in
  check)
    if compare_payload; then
      printf '%s\n' 'Overleaf selected payload is already synchronized.'
    else
      printf '%s\n' 'Overleaf selected payload differs; rerun with --apply after reviewing the diff.' >&2
      exit 1
    fi
    ;;
  apply)
    assert_clean_target
    apply_payload
    compile_target
    git -C "$target_dir" diff --check
    git -C "$target_dir" status --short
    ;;
  push)
    if [[ -n "$(git -C "$target_dir" status --porcelain)" ]]; then
      assert_only_selected_payload_changes
      if ! compare_payload; then
        printf '%s\n' 'Dirty selected payload does not match the local canonical source.' >&2
        exit 2
      fi
    else
      apply_payload
    fi
    compile_target
    git -C "$target_dir" diff --check
    stage_payload
    if git -C "$target_dir" diff --cached --quiet; then
      printf '%s\n' 'No selected manuscript changes to commit or push.'
      exit 0
    fi
    git -C "$target_dir" commit -m "$commit_message"
    git -C "$target_dir" push origin main
    ;;
esac

printf 'Local repository root: %s\n' "$repo_root"
