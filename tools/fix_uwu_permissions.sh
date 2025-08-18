#!/bin/bash

PROJECT_ROOT="/var/www/html"
USER="kanis"
GROUP="uwu"

echo "[*] Correction des permissions pour $PROJECT_ROOT"

# 1. Propriété correcte
sudo chown -R "$USER":"$GROUP" "$PROJECT_ROOT"

# 2. Fichiers : lecture/écriture (664)
find "$PROJECT_ROOT" -type f ! -path "$PROJECT_ROOT/venv/*" -exec chmod 664 {} \;

# 3. Dossiers : lecture/écriture/exécution + setgid (2775)
find "$PROJECT_ROOT" -type d ! -path "$PROJECT_ROOT/venv/*" -exec chmod 2775 {} \;
find "$PROJECT_ROOT" -type d ! -path "$PROJECT_ROOT/venv/*" -exec chmod g+s {} \;

# 4. Script exécutable UwU GUI s’il existe
chmod +x "$PROJECT_ROOT/uwu_gui.py"

# 5. Script CLI ou outils
find "$PROJECT_ROOT/tools" -type f -name "*.sh" -exec chmod +x {} \;

echo "[OK] Permissions corrigées pour tous les fichiers du projet UwU Logs."

