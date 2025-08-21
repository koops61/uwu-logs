# UwU Logs

<https://uwu-logs.xyz/>

UwU Logs is a World of Warcraft combat log parser.

Supports any Wrath of the Lich King (3.3.5) server.

❤️ Inspired by World of Logs, LegacyPlayers and Warcraft Logs.


## Nouveautés de ce fork (koops61)

- `logs_auto.py` : pipeline auto qui crée/alimente les bases **Top** et **Gear** à partir des reports.
- `reparse_all.py` : relance le parsing de tout `uploads/uploaded` (utile après une mise à jour).
- **Création auto** des bases SQLite `db/top/*.db` et `db/gear/*.db` si absentes (schéma correct).
- `.gitignore` renforcé (les fichiers générés ne polluent plus le dépôt).
- **Dashboard local** `uwu_gui.py` (Tkinter) : contrôle de services, stats live, tail de logs, lancement de scripts, init DB, cron. 

---

## Self hosting

- Install packages from `requirements.txt`

# pour le GUI Tkinter (Debian/Ubuntu)
sudo apt-get install -y python3-tk

# optionnel : psutil pour des stats système plus précises
pip install psutil

---
## Dashboard local : uwu_gui.py 
   Un petit dashboard Tkinter pour piloter la stack localement.
   Lancer : python uwu_gui.py  "Nécessite : python3-tk (Tkinter). psutil est facultatif (le script a un fallback /proc)."

<img width="1345" height="753" alt="image" src="https://github.com/user-attachments/assets/c58eba09-557b-4f07-a959-71a083cbeaab" />


Fonctions

Services systemd : Start / Stop / Restart / Status pour
server_5000 (site), server_5010 (top), server_5020 (upload).

Stats live : CPU, RAM, disque (via psutil si présent, sinon fallback).

Logs : sélection d’un fichier et Tail 200; affiche aussi la sortie en direct des scripts lancés.

Scripts :

Lancer logs_auto.py

Init/Check DB (Top + Gear) : crée/valide les schémas et insère un sample minimal si besoin

Cron (utilisateur) :

Afficher la crontab

Assurer l’entrée cron (une seule ligne) pour logs_auto.py toutes les 2 minutes

Configuration (en haut du fichier)

BASE_DIR : /var/www/html

VENV_PY : venv/bin/python si présent

SERVICES : server_5000, server_5010, server_5020

LOG_CANDIDATES : fichiers à proposer par défaut dans la section Logs

Droits sudo (contrôle systemd depuis le GUI)

Si tu veux cliquer Start/Stop sans mot de passe : sudo visudo -f /etc/sudoers.d/uwu-logs

Exemple (remplace username par le votre) : 
username ALL=(ALL) NOPASSWD: /bin/systemctl start server_5000.service, /bin/systemctl stop server_5000.service, /bin/systemctl restart server_5000.service, /bin/systemctl status server_5000.service, /bin/systemctl start server_5010.service, /bin/systemctl stop server_5010.service, /bin/systemctl restart server_5010.service, /bin/systemctl status server_5010.service, /bin/systemctl start server_5020.service, /bin/systemctl stop server_5020.service, /bin/systemctl restart server_5020.service, /bin/systemctl status server_5020.service

Dans le GUI :

coche “Utiliser sudo” si nécessaire ;

si tu as configuré NOPASSWD, coche “sudo -n (non interactif)” ;

sinon, décoche “sudo -n” et lance le GUI depuis un terminal pour pouvoir entrer ton mot de passe.

Permissions des logs (important)

Les services écrivent dans /_loggers.
Assure-toi que le répertoire existe et est écrit par l’utilisateur qui lance les services (www-data en prod) :

sudo mkdir -p /var/www/html/_loggers
sudo chown -R www-data:www-data /var/www/html/_loggers
sudo chmod 775 /var/www/html/_loggers

Cron (uniquement logs_auto.py)

Exemple d’entrée (toutes les 2 minutes) Le dashboard peut l’ajouter automatiquement (menu Cron > “Assurer l’entrée UwU Logs”). :


*/2 * * * * cd /var/www/html && /var/www/html/venv/bin/python /var/www/html/logs_auto.py >> /home/$USER/logs/logs_auto.log 2>&1


---

- Run `python Z_SERVER.py` OR `gunicorn3 Z_SERVER:SERVER --port 5000 -D`

- Visit <http://localhost:5000/>

#### Optional
##### Top

- Run `python server_top.py` OR `uvicorn server_top:app --port 5020 --proxy-headers`

##### File uploads

- Run `python server_upload.py` OR `uvicorn server_upload:app --port 5010 --proxy-headers`

##### Download spells/classes icons pack

- [Google Drive download](https://drive.google.com/file/d/17DyiCJts01CkFIkd0-G1dVAypIlxd0pP)

- Extract to root folder.

## Showcase

### Top

<https://uwu-logs.xyz/top>

![Showcase top](https://raw.githubusercontent.com/Ridepad/uwu-logs/main/static/thumb.png)

### PvE Statistics

<https://uwu-logs.xyz/top_stats>

![Showcase PvE statistics](https://raw.githubusercontent.com/Ridepad/uwu-logs/main/showcase/pve_stats.png)

### Player total and per target spell info

![Showcase player spell info](https://raw.githubusercontent.com/Ridepad/uwu-logs/main/showcase/spell_info.png)

### Damage to targets + useful

![Showcase useful](https://raw.githubusercontent.com/Ridepad/uwu-logs/main/showcase/useful.png)

### Player comparison

![Showcase comparison](https://raw.githubusercontent.com/Ridepad/uwu-logs/main/showcase/compare.png)

### Spell search and overall info

![Showcase spell search](https://raw.githubusercontent.com/Ridepad/uwu-logs/main/showcase/spells.png)

### Consumables

![Showcase consumables](https://raw.githubusercontent.com/Ridepad/uwu-logs/main/showcase/consume.png)

## TODO

- friendly fire: Bloodbolt Splash, ucm, vortex
- self harm: ucm, Chilled to the Bone
- site side logs parser - filter forms - guid spell etc

- portal stacks
- valk grabs + necrotic + defile targets

- fix unlogical buff duration max 30 sec? last combat log entry? filter out long spells - ff hmark
- if buff not in long_buffs check top50% avg of this buff

- add summary stats like max hit done max hit taken max absorb max grabs
- 1 tick total - all targets dmg from 1 hurricane tick or typhoon
