#!/bin/bash

# Détecte dynamiquement l'utilisateur qui exécute le script
USER="$(whoami)"
GROUP="uwu"
PROJECT_ROOT="/var/www/html"

echo "[*] Correction des permissions pour $PROJECT_ROOT"
echo "[*] Utilisateur actuel : $USER"

# 1. Propriété correcte (hors venv)
sudo chown -R "$USER":"$GROUP" "$PROJECT_ROOT"

# 2. Fichiers : lecture/écriture (664), sauf le venv
find "$PROJECT_ROOT" -type f ! -path "$PROJECT_ROOT/venv/*" -exec chmod 664 {} \;

# 3. Dossiers : lecture/écriture/exécution + setgid (2775), sauf le venv
find "$PROJECT_ROOT" -type d ! -path "$PROJECT_ROOT/venv/*" -exec chmod 2775 {} \;
find "$PROJECT_ROOT" -type d ! -path "$PROJECT_ROOT/venv/*" -exec chmod g+s {} \;

# 4. Script UwU GUI
chmod +x "$PROJECT_ROOT/uwu_gui.py"

# 5. Scripts shell & Python dans tools/
find "$PROJECT_ROOT/tools" -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod +x {} \;

# 6. Binaire 7zz
if [ -f "$PROJECT_ROOT/7zz" ]; then
    chmod +x "$PROJECT_ROOT/7zz"
    echo "[+] 7zz rendu exécutable"
fi

echo "[OK] Permissions corrigées pour tous les fichiers du projet UwU Logs."
