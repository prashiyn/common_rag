#!/usr/bin/env bash
# Prepend deprecation notice to README.md on standalone GitHub repos before archiving.
set -euo pipefail

MOVED_MARKER="# Moved"

# repo_name:monorepo_path
REPOS=(
  "llm-service:llm-service"
  "doc_processing:doc_processing"
  "core_rag_graph:core_rag_graph"
  "ra_literag:ra_literag"
  "temporial_graph:temporial_graph"
  "temporial_graph_openai:temporial_graph_openai"
  "temporial_graph_traversal:temporial_graph_traversal"
  "fin_rag:fin_rag"
)

banner_for() {
  local path="$1"
  cat <<EOF
# Moved

This service now lives in the [common_rag](https://github.com/prashiyn/common_rag) monorepo under \`${path}/\`.
EOF
}

prepend_banner() {
  local file="$1"
  local path="$2"
  local banner
  banner="$(banner_for "$path")"

  if [[ -f "$file" ]] && grep -qF "$MOVED_MARKER" "$file"; then
    echo "  skip: deprecation banner already present"
    return 0
  fi

  if [[ -f "$file" ]]; then
    {
      printf '%s\n\n' "$banner"
      printf '%s\n' '---'
      printf '\n'
      cat "$file"
    } >"${file}.new"
    mv "${file}.new" "$file"
  else
    printf '%s\n' "$banner" >"$file"
  fi
}

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

# Use monorepo author for ephemeral clone commits (no git config changes).
if git -C "${BASH_SOURCE[0]%/*}/.." log -1 --format='%an|%ae' >/dev/null 2>&1; then
  IFS='|' read -r GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL < <(
    git -C "${BASH_SOURCE[0]%/*}/.." log -1 --format='%an|%ae'
  )
  export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL
  export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
  export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
fi

for entry in "${REPOS[@]}"; do
  repo="${entry%%:*}"
  path="${entry##*:}"
  echo "=== prashiyn/${repo} -> ${path}/ ==="
  rm -rf "${WORKDIR}/${repo}"
  git clone --depth 1 "git@github.com:prashiyn/${repo}.git" "${WORKDIR}/${repo}"
  pushd "${WORKDIR}/${repo}" >/dev/null
  prepend_banner README.md "$path"
  if git status --porcelain README.md | grep -q .; then
    git add README.md
    git commit -m "docs: point README to common_rag monorepo before archive"
    git push origin HEAD
    echo "  pushed deprecation README"
  else
    echo "  no changes to commit"
  fi
  popd >/dev/null
done

echo "Done."
