# Claude Code API switching aliases

# MiMo API で claude を起動
# コンテナ内: /run/secrets/mimo.env (bind mount)
# WSLホスト: ~/.claude/mimo.env
_mimo_env() { [ -f /run/secrets/mimo.env ] && echo /run/secrets/mimo.env || echo ~/.claude/mimo.env; }
alias claude-mimo='source "$(_mimo_env)" && claude'

# Anthropic 公式 OAuth で claude を起動（MiMo env vars を明示的にクリア）
alias claude-official='env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN \
  -u ANTHROPIC_MODEL -u ANTHROPIC_DEFAULT_SONNET_MODEL \
  -u ANTHROPIC_DEFAULT_OPUS_MODEL -u ANTHROPIC_DEFAULT_HAIKU_MODEL \
  claude'
