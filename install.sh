#!/usr/bin/env bash
# dotfiles install script - creates symlinks from dotfiles to home directory
set -e

DOTFILES="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$HOME/.dotfiles-backup/$(date +%Y%m%d_%H%M%S)"

backup_and_link() {
  local src="$1"  # dotfiles内のパス
  local dst="$2"  # リンク先（ホームの実際のパス）
  local rel="$3"  # dstから見たsrcへの相対パス

  mkdir -p "$(dirname "$dst")"

  # 既にリンク先が正しいsymlinkなら何もしない
  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$rel" ]; then
    echo "  skip (already linked): $dst"
    return
  fi

  # 実ファイルが存在する場合はバックアップ
  if [ -e "$dst" ] && [ ! -L "$dst" ]; then
    mkdir -p "$BACKUP_DIR"
    cp -r "$dst" "$BACKUP_DIR/"
    echo "  backup: $dst → $BACKUP_DIR/"
    rm -rf "$dst"
  elif [ -L "$dst" ]; then
    rm "$dst"
  fi

  ln -s "$rel" "$dst"
  echo "  linked: $dst → $rel"
}

echo "==> Installing dotfiles..."

# git
backup_and_link \
  "$DOTFILES/git/.gitconfig" \
  "$HOME/.gitconfig" \
  ".dotfiles/git/.gitconfig"

# claude aliases & settings（相対symlinkでホスト・コンテナ両対応）
mkdir -p "$HOME/.claude"
backup_and_link \
  "$DOTFILES/bash/aliases.sh" \
  "$HOME/.claude/bash_aliases.sh" \
  "../.dotfiles/bash/aliases.sh"

backup_and_link \
  "$DOTFILES/claude/settings.local.json" \
  "$HOME/.claude/settings.local.json" \
  "../.dotfiles/claude/settings.local.json"

# .bashrc に source 行を追記（重複しない）
BASHRC="$HOME/.bashrc"
SOURCE_LINE='[ -f ~/.dotfiles/bash/aliases.sh ] && source ~/.dotfiles/bash/aliases.sh'
if ! grep -qF "$SOURCE_LINE" "$BASHRC" 2>/dev/null; then
  echo "" >> "$BASHRC"
  echo "# dotfiles" >> "$BASHRC"
  echo "$SOURCE_LINE" >> "$BASHRC"
  echo "  updated: ~/.bashrc"
fi

echo "==> Done!"
