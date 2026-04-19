#!/usr/bin/env bash
# 新マシン・新WSL環境セットアップ用
# 使い方: curl -fsSL https://raw.githubusercontent.com/CauchyLee1981/.dotfiles/main/bootstrap.sh | bash
set -e

DOTFILES_DIR="$HOME/.dotfiles"
DOTFILES_REPO="https://github.com/CauchyLee1981/.dotfiles.git"

if [ -d "$DOTFILES_DIR" ]; then
  echo "==> Updating existing dotfiles..."
  git -C "$DOTFILES_DIR" pull
else
  echo "==> Cloning dotfiles..."
  git clone "$DOTFILES_REPO" "$DOTFILES_DIR"
fi

bash -v "$DOTFILES_DIR/install.sh"
