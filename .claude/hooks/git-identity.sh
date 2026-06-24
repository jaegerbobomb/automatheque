#!/usr/bin/env bash
# Hook SessionStart : restaure l'identité git et la signature SSH de dwwm93
# dans les sessions Claude Code (web/remote), à CHAQUE démarrage ou reprise.
#
# Pourquoi ce hook existe
# -----------------------
# Le conteneur cloud est éphémère et un hook « launcher » de la plateforme
# (hors dépôt) réécrit l'identité git GLOBALE en « Claude <noreply@anthropic.com> »
# à chaque (re)démarrage de session. On ne peut pas garantir l'ordre d'exécution
# des hooks ; on écrit donc la configuration au niveau LOCAL du dépôt
# (.git/config), qui prime toujours sur --global. L'identité dwwm93 gagne donc
# quel que soit l'ordre.
#
# Sûreté pour les autres
# ----------------------
# No-op si SIGNING_SSH_KEY est absent (clé fournie uniquement via la config
# d'environnement de dwwm93). Pour tout autre contributeur, ou en session
# locale, ce hook ne fait donc rien.
set -uo pipefail

# Rien à faire si la clé de signature n'est pas dans l'environnement.
[ -n "${SIGNING_SSH_KEY:-}" ] || exit 0
command -v ssh-keygen >/dev/null 2>&1 || exit 0

REPO="${CLAUDE_PROJECT_DIR:-$PWD}"
cd "$REPO" 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

EMAIL="74361568+dwwm93@users.noreply.github.com"
NAME="dwwm93"
SSH_DIR="$HOME/.ssh"
KEY="$SSH_DIR/commit_signing_key"
PUB="$KEY.pub"
ALLOWED="$SSH_DIR/allowed_signers"

# (Re)matérialise la clé privée + publique + allowed_signers depuis l'env.
umask 077
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
printf '%s\n' "$SIGNING_SSH_KEY" >"$KEY"
ssh-keygen -y -P "" -f "$KEY" >"$PUB" 2>/dev/null || exit 0
printf '%s %s\n' "$EMAIL" "$(cat "$PUB")" >"$ALLOWED"
chmod 600 "$KEY"
chmod 644 "$PUB" "$ALLOWED"

# Config LOCALE au dépôt : prime sur le --global réécrit par la plateforme,
# indépendamment de l'ordre des hooks SessionStart.
git config --local user.name "$NAME"
git config --local user.email "$EMAIL"
git config --local commit.gpgsign true
git config --local gpg.format ssh
git config --local gpg.ssh.program ssh-keygen
git config --local user.signingkey "$PUB"
git config --local gpg.ssh.allowedSignersFile "$ALLOWED"

echo "[git-identity] identité+signature dwwm93 rétablies (config locale du dépôt)" >&2
exit 0
