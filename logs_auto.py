'''
This file runs in a cron job on the server.
Example (every minute with a lock):
*/1 * * * * /usr/bin/flock -n /tmp/fcj.lockfile /usr/bin/python3 /home/uwu-logs/logs_auto.py

For testing, run it when needed manually.
'''

<<<<<<< HEAD
=======
# imports (en haut du fichier)
>>>>>>> a94d2b1 (Initial commit du projet uwu-logs avec mes modifs)
import itertools
import os
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from time import perf_counter

<<<<<<< HEAD
=======
from functools import partial
import top_gear as TG          # <= un seul import de top_gear
import parser_profile as P
>>>>>>> a94d2b1 (Initial commit du projet uwu-logs avec mes modifs)
import api_7z
import api_top_db_v2
import logs_calendar
import logs_top
from constants import DEFAULT_SERVER_NAME
from c_path import Directories, FileNames
from h_debug import Loggers, get_ms_str
from h_other import get_report_name_info

LOGGER_UPLOADS = Loggers.uploads

<<<<<<< HEAD
=======
# OK de s'assurer que le dossier existe au chargement
Directories.gear.mkdir(parents=True, exist_ok=True)
>>>>>>> a94d2b1 (Initial commit du projet uwu-logs avec mes modifs)

def remove_old_dublicate(report_id: str):
    if DEFAULT_SERVER_NAME in report_id:
        return
    
    _server = get_report_name_info(report_id)["server"]
    report_id_old = report_id.replace(_server, DEFAULT_SERVER_NAME)
    archive_path_old = Directories.archives.joinpath(f"{report_id_old}.7z")
    if archive_path_old.is_file():
        archive_path_old.unlink()

def save_raw_logs(report_id: str):
    pending_text = Directories.pending_archive / f"{report_id}.txt"
    if not pending_text.is_file():
        return
    
    pc = perf_counter()
    Directories.archives.mkdir(exist_ok=True)
    archive_path = Directories.archives / f"{report_id}.7z"
    archive = api_7z.SevenZipArchive(archive_path)
    return_code = archive.create(pending_text)
    if return_code == 0:
<<<<<<< HEAD
        pending_text.unlink()
=======
        try:
            if pending_text.is_file():
                pending_text.unlink()
        except FileNotFoundError:
            pass
>>>>>>> a94d2b1 (Initial commit du projet uwu-logs avec mes modifs)
        remove_old_dublicate(report_id)
        LOGGER_UPLOADS.debug(f'{get_ms_str(pc)} | {report_id:50} | Saved raw')
        return
    
    LOGGER_UPLOADS.debug(f'{get_ms_str(pc)} | {report_id:50} | ERROR {return_code}')

def _report_server(report_id: str):
    return get_report_name_info(report_id)["server"]

def top_has_errors(data: list[dict]):
    for row in data:
        for key in {"u", "d", "t"}:
            if not row.get(key):
                if row.get(key) == 0:
                    continue
                LOGGER_UPLOADS.error(f'top_has_errors | {key} | {row}')
                return True
    return False

def gen_top_data(top_data: dict):
    for boss_name, modes in top_data.items():
        for mode, data in modes.items():
            table_name = api_top_db_v2.TopDB.get_table_name(boss_name, mode)
            yield table_name, data

<<<<<<< HEAD

def add_new_top_data(server, reports):
    top_data: dict[str, dict[str, list[dict]]]

=======
def get_players_from_top(top_data: dict) -> set[str]:
    players = set()
    for _table_name, data in gen_top_data(top_data):
        for row in data:
            name = row.get("player") or row.get("name") or row.get("n")
            if name:
                players.add(name)
    return players

def build_gear_for_reports(server: str, reports: list[str]):
    """
    Lit les tops des reports du serveur, récupère la liste unique de joueurs
    et alimente la DB gear du serveur (créée si absente) via parser_profile.
    """
    # 1) Init/Création de la DB gear avec le BON schéma
    try:
        # new=True => crée le fichier + schéma si absent, sinon ouvre existant
        TG.GearDB(server, new=True)
    except Exception:
        LOGGER_UPLOADS.exception(f"Cannot init GearDB for server={server}")
        return

    # 1bis) Forcer parser_profile à utiliser GearDB(new=True)
    # (ainsi, son appel GearDB(server) créera la DB si besoin)
    P.GearDB = partial(TG.GearDB, new=True)

    # 2) Choix de la/les fonctions de parser_profile disponibles
    use_player = hasattr(P, "parse_and_save_player")
    use_wrap   = hasattr(P, "parse_and_save_wrap")
    if not (use_player or use_wrap):
        LOGGER_UPLOADS.error("No gear parse function found in parser_profile")
        return

    # 3) Collecte des joueurs depuis les tops
    all_players = set()
    for report_id in reports:
        top_file = Directories.logs.joinpath(report_id, FileNames.logs_top)
        if not top_file.is_file():
            continue
        try:
            top_data = top_file.json()
            all_players |= get_players_from_top(top_data)
        except Exception:
            LOGGER_UPLOADS.exception(f"Error reading top file for {report_id}")

    if not all_players:
        return

    # 4) Parse & sauvegarde du gear
    for name in sorted(all_players):
        try:
            player_obj = {"name": name, "server": server}  # attendu par parser_profile
            if use_player:
                P.parse_and_save_player(player_obj)
            elif use_wrap:
                try:
                    P.parse_and_save_wrap(player_obj)
                except TypeError:
                    P.parse_and_save_wrap(name)

            LOGGER_UPLOADS.debug(f"Saved gear | {name:30} | {server}")
        except Exception:
            LOGGER_UPLOADS.exception(f"Gear parse error | {name} | {server}")


def add_new_top_data(server, reports):
>>>>>>> a94d2b1 (Initial commit du projet uwu-logs avec mes modifs)
    pc = perf_counter()

    errors = set()
    _data = defaultdict(list)
    for report_id in reports:
        top_file = Directories.logs.joinpath(report_id, FileNames.logs_top)
        top_data = top_file.json()
        for table_name, data in gen_top_data(top_data):
            if top_has_errors(data):
                errors.add(report_id)
                break
            _data[table_name].extend(data)

<<<<<<< HEAD
    api_top_db_v2.TopDB(server, new=True).add_new_entries_wrap(_data)
    
    LOGGER_UPLOADS.debug(f'{get_ms_str(pc)} | Saved top | {server}')

    return errors

=======
    # crée/ouvre la DB TOP (comme avant)
    api_top_db_v2.TopDB(server, new=True).add_new_entries_wrap(_data)

    LOGGER_UPLOADS.debug(f'{get_ms_str(pc)} | Saved top | {server}')
    return errors


>>>>>>> a94d2b1 (Initial commit du projet uwu-logs avec mes modifs)
def group_reports_by_server(new_logs):
    new_logs = sorted(new_logs, key=_report_server)
    return itertools.groupby(new_logs, key=_report_server)

def _make_report_top_wrap(report_id: str):
    done = logs_top.make_report_top_wrap(report_id)
    return report_id, done

def make_top_data(new_logs: list[str], processes: int=1):
    if processes > 1:
        with ProcessPoolExecutor(max_workers=processes) as executor:
            done_data = executor.map(_make_report_top_wrap, new_logs)
    else:
        done_data = [
            _make_report_top_wrap(report_id)
            for report_id in new_logs
        ]

    return (
        report_id
        for report_id, done in done_data
        if not done
    )

def add_to_archives(new_logs: list[str], processes: int=1):
    api_7z.SevenZip().download()

    if processes > 1:
        with ProcessPoolExecutor(max_workers=processes) as executor:
            executor.map(save_raw_logs, new_logs)
    else:
        for report_id in new_logs:
            save_raw_logs(report_id)

def remove_errors(reports: list, errors: list, func="?"):
    for report_id in errors:
        LOGGER_UPLOADS.error(f'Removed due to error | {report_id}')
        
        try:
            reports.remove(report_id)
        except Exception:
            pass

    print(f"logs left {len(reports):3} {func}")

def main(multiprocessing=True):
    if not Directories.pending_archive.is_dir():
        return
    
    NEW_LOGS = [
        file_path.stem
        for file_path in Directories.pending_archive.iterdir()
        if file_path.suffix == ".txt"
    ]
    if not NEW_LOGS:
        return

    if multiprocessing:
        MAX_CPU = max(os.cpu_count() - 1, 1)
    else:
        MAX_CPU = 1

    errors = make_top_data(NEW_LOGS, MAX_CPU)
    remove_errors(NEW_LOGS, errors, func="make_top_data")

    errors = set()
    for server, reports in group_reports_by_server(NEW_LOGS):
        new_errors = add_new_top_data(server, reports)
        errors.update(new_errors)

    remove_errors(NEW_LOGS, errors, func="add_new_top_data")

<<<<<<< HEAD
=======
    # === Build/Update gear DB par serveur, à partir des reports traités ===
    for server, reports_iter in group_reports_by_server(NEW_LOGS):
        reports = list(reports_iter)  # matérialiser l’itérateur !
        build_gear_for_reports(server, reports)
    # === fin gear ===


>>>>>>> a94d2b1 (Initial commit du projet uwu-logs avec mes modifs)
    # needs player and encounter data, thats why after logs top
    logs_calendar.add_new_logs(NEW_LOGS)

    add_to_archives(NEW_LOGS, MAX_CPU)

    for report_id in NEW_LOGS:
        tz_path = Directories.pending_archive / f"{report_id}.timezone"
        if tz_path.is_file():
            tz_path.unlink()

def main_wrap():
    no_debug = "--debug" not in sys.argv
    pc = perf_counter()
    try:
        LOGGER_UPLOADS.debug(f'{get_ms_str(pc)} | Auto start')
        main(multiprocessing=no_debug)
        LOGGER_UPLOADS.debug(f'{get_ms_str(pc)} | Auto finish')
    except Exception:
        LOGGER_UPLOADS.exception(f'{get_ms_str(pc)} | Auto error')

if __name__ == '__main__':
    main_wrap()
