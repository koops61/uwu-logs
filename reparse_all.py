#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reparse tous les reports trouvés dans uploads/uploaded et/ou LogsDir.
- (Re)génère les tops et les insère en DB TOP (schéma TOP)
- Construit/alimente la DB Gear (schéma Gear) via parser_profile

Exemples :
  # dry-run pour voir ce qui serait traité depuis uploads/uploaded
  python reparse_all.py --source uploaded --dry-run

  # reparse tout (tops + gear) depuis uploads/uploaded
  python reparse_all.py --source uploaded

  # reparse seulement les gears
  python reparse_all.py --only-gear --source both

  # filtrer par serveur
  python reparse_all.py --server Lordaeron
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from typing import Iterable, Iterator

import api_top_db_v2
import logs_top
import parser_profile as P
import top_gear

from c_path import Directories, FileNames
from constants import DEFAULT_SERVER_NAME
from h_debug import Loggers, get_ms_str
from h_other import get_report_name_info

LOGGER = Loggers.uploads  # réutilise la conf de log existante


# ---------- utils noms/serveurs ----------

def report_server(report_id: str) -> str:
    """Extrait le nom de serveur d’un report_id via h_other.get_report_name_info."""
    try:
        return get_report_name_info(report_id)["server"]
    except Exception:
        return DEFAULT_SERVER_NAME


def group_by_server(report_ids: Iterable[str]) -> Iterator[tuple[str, list[str]]]:
    """Regroupe une liste de report_ids par serveur (ordre stable)."""
    buckets: dict[str, list[str]] = defaultdict(list)
    for rid in report_ids:
        buckets[report_server(rid)].append(rid)
    for server, rids in buckets.items():
        yield server, rids


# ---------- lecture uploads/uploaded ----------

def _candidates_uploaded_dirs() -> list[Path]:
    """Retourne une liste ordonnée de dossiers possibles pour uploads/uploaded."""
    cands: list[Path] = []

    # 1) attribut connu dans Directories (si présent dans ta base)
    up = getattr(Directories, "uploaded", None)
    if isinstance(up, Path):
        cands.append(up)

    # 2) proximité de pending_archive : ./uploads/uploaded
    if hasattr(Directories, "pending_archive"):
        cands.append(Directories.pending_archive.parent / "uploaded")

    # 3) chemins classiques
    cands += [
        Path("/var/www/html/uploads/uploaded"),
        Path("/home/uwu-logs/uploads/uploaded"),
        Path.cwd() / "uploads" / "uploaded",
    ]

    out, seen = [], set()
    for d in cands:
        if d and d.exists() and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def list_report_ids_from_uploaded(uploaded_dir: Path) -> tuple[list[str], dict]:
    """
    Accepte :
      - fichiers .txt (stem = report_id)
      - fichiers .7z  (stem = report_id)
      - dossiers nommés comme '25-..--Name--Server'
    Retourne (report_ids_uniques, stats_par_type)
    """
    ids: list[str] = []
    stats = {"txt": 0, "7z": 0, "dir": 0, "autre": 0}

    for p in sorted(uploaded_dir.iterdir()):
        if p.is_file() and p.suffix == ".txt":
            ids.append(p.stem); stats["txt"] += 1
        elif p.is_file() and p.suffix == ".7z":
            ids.append(p.stem); stats["7z"] += 1
        elif p.is_dir():
            ids.append(p.name); stats["dir"] += 1
        else:
            stats["autre"] += 1

    # dédoublonnage
    seen, out = set(), []
    for rid in ids:
        if rid not in seen:
            seen.add(rid)
            out.append(rid)
    return out, stats


# ---------- lecture LogsDir ----------

def list_report_ids_from_logsdir() -> list[str]:
    """Liste les dossiers dans LogsDir qui contiennent un fichier logs_top.json."""
    out = []
    for d in sorted(Directories.logs.iterdir()):
        if d.is_dir() and (d / FileNames.logs_top).is_file():
            out.append(d.name)
    return out


# ---------- sélection source ----------

def resolve_report_ids(source: str, dry_run: bool = False) -> tuple[list[str], dict[str, int]]:
    """
    source ∈ {"uploaded", "logs", "both"}
    Retourne (report_ids, stats) avec compteurs par source.
    """
    stats = {"uploaded": 0, "logs": 0}
    uploaded_ids: list[str] = []
    logs_ids: list[str] = []

    if source in ("uploaded", "both"):
        uploaded_dirs = _candidates_uploaded_dirs()
        total_ids: list[str] = []
        if uploaded_dirs:
            for up in uploaded_dirs:
                ids, up_stats = list_report_ids_from_uploaded(up)
                if ids:
                    LOGGER.debug(
                        f"reparse_all | uploaded dir détecté: {up} | "
                        f"{len(ids)} reports (txt={up_stats['txt']} 7z={up_stats['7z']} dir={up_stats['dir']} autre={up_stats['autre']})"
                    )
                    if dry_run:
                        LOGGER.debug("reparse_all | échantillon uploaded: " + ", ".join(ids[:8]))
                total_ids.extend(ids)
        else:
            LOGGER.debug("reparse_all | aucun dossier uploaded détecté")

        # dédoublonnage global
        seen, uploaded_ids = set(), []
        for rid in total_ids:
            if rid not in seen:
                seen.add(rid)
                uploaded_ids.append(rid)

        if not uploaded_ids:
            LOGGER.debug("reparse_all | aucun report dans les dossiers uploaded détectés")

        stats["uploaded"] = len(uploaded_ids)

    if source in ("logs", "both"):
        logs_ids = list_report_ids_from_logsdir()
        LOGGER.debug(f"reparse_all | logs/ trouvé(s): {len(logs_ids)} reports")
        if dry_run and logs_ids:
            LOGGER.debug("reparse_all | échantillon logs: " + ", ".join(logs_ids[:8]))
        stats["logs"] = len(logs_ids)

    # combinaison suivant la source
    combined: list[str] = []
    seen = set()
    src_seq = []
    if source == "uploaded":
        src_seq = uploaded_ids
    elif source == "logs":
        src_seq = logs_ids
    else:  # both
        src_seq = uploaded_ids + logs_ids

    for rid in src_seq:
        if rid not in seen:
            seen.add(rid)
            combined.append(rid)

    return combined, stats


# ---------- TOP (parse + DB) ----------

def gen_top_data(top_data: dict) -> Iterator[tuple[str, list[dict]]]:
    """Itère (table_name, data_list) pour insertion dans la DB TOP."""
    for boss_name, modes in top_data.items():
        for mode, data in modes.items():
            table_name = api_top_db_v2.TopDB.get_table_name(boss_name, mode)
            yield table_name, data


def add_top_for_server(server: str, reports: list[str]) -> set[str]:
    """
    Pour un serveur donné, (re)génère les tops des reports fournis,
    et écrit en DB TOP (schéma TOP). Renvoie l’ensemble des reports en erreur.
    """
    errors: set[str] = set()
    pc = perf_counter()
    _data = defaultdict(list)

    for report_id in reports:
        # assure/génère le top (créera LogsDir/<report_id>/logs_top.json)
        try:
            logs_top.make_report_top_wrap(report_id)
        except Exception:
            LOGGER.exception(f"top error | make_report_top_wrap | {report_id}")
            errors.add(report_id)
            continue

        top_file = Directories.logs.joinpath(report_id, FileNames.logs_top)
        if not top_file.is_file():
            LOGGER.error(f"top missing | {report_id} | {top_file}")
            errors.add(report_id)
            continue

        try:
            top_json = top_file.json()
            for table_name, data in gen_top_data(top_json):
                _data[table_name].extend(data)
        except Exception:
            LOGGER.exception(f"top read/merge error | {report_id}")
            errors.add(report_id)
            continue

    if _data:
        try:
            api_top_db_v2.TopDB(server, new=True).add_new_entries_wrap(_data)
            LOGGER.debug(f"{get_ms_str(pc)} | Saved top | {server}")
        except Exception:
            LOGGER.exception(f"{get_ms_str(pc)} | top db write error | {server}")

    return errors


# ---------- GEAR (parse + DB) ----------

def get_players_from_top(top_data: dict) -> set[str]:
    players = set()
    for _table_name, data in gen_top_data(top_data):
        for row in data:
            name = row.get("player") or row.get("name") or row.get("n")
            if name:
                players.add(name)
    return players


def add_gear_for_server(server: str, reports: list[str]) -> None:
    """
    Crée si besoin la DB gear (schéma gear), puis parse/sauvegarde le gear
    pour tous les joueurs présents dans les tops des reports donnés.
    """
    # 1) s'assurer que la DB gear existe (schéma gear)
    try:
        top_gear.GearDB(server, new=True)
    except Exception:
        LOGGER.exception(f"Cannot init GearDB for server={server}")
        return

    # 2) choisir la fonction parser_profile disponible
    use_player = hasattr(P, "parse_and_save_player")
    use_wrap   = hasattr(P, "parse_and_save_wrap")
    if not (use_player or use_wrap):
        LOGGER.error("No gear parse function found in parser_profile")
        return

    # 3) collecter les joueurs depuis les tops des reports
    all_players = set()
    for report_id in reports:
        top_file = Directories.logs.joinpath(report_id, FileNames.logs_top)
        if not top_file.is_file():
            continue
        try:
            top_json = top_file.json()
            all_players |= get_players_from_top(top_json)
        except Exception:
            LOGGER.exception(f"Error reading top file for {report_id}")

    if not all_players:
        return

    # 4) parse & save
    for name in sorted(all_players):
        try:
            player_obj = {"name": name, "server": server}
            if use_player:
                P.parse_and_save_player(player_obj)
            else:
                try:
                    P.parse_and_save_wrap(player_obj)
                except TypeError:
                    P.parse_and_save_wrap(name)
            LOGGER.debug(f"Saved gear | {name:30} | {server}")
        except Exception:
            LOGGER.exception(f"Gear parse error | {name} | {server}")


# ---------- run ----------

def run(server_filter: list[str] | None,
        limit: int | None,
        only_top: bool,
        only_gear: bool,
        workers: int,
        source: str,
        dry_run: bool) -> None:

    pc = perf_counter()
    report_ids, stats = resolve_report_ids(source, dry_run=dry_run)

    # filtrage éventuel par serveur
    if server_filter:
        keep = []
        sset = set(server_filter)
        for rid in report_ids:
            if report_server(rid) in sset:
                keep.append(rid)
        report_ids = keep

    total_before = len(report_ids)
    if limit and total_before > limit:
        report_ids = report_ids[:limit]

    LOGGER.debug(f"reparse_all | stats: uploaded={stats['uploaded']} logs={stats['logs']} | retenus={len(report_ids)}")
    if not report_ids:
        LOGGER.debug("reparse_all | rien à faire (aucun report_id éligible)")
        return

    if dry_run:
        LOGGER.debug("DRY-RUN | exemples: " + ", ".join(report_ids[:10]))
        LOGGER.debug("DRY-RUN | arrêt ici.")
        return

    # groupage par serveur
    for server, rlist in group_by_server(report_ids):
        # TOP
        if not only_gear:
            add_top_for_server(server, rlist)

        # GEAR
        if not only_top:
            add_gear_for_server(server, rlist)

    LOGGER.debug(f"{get_ms_str(pc)} | reparse_all terminé | {len(report_ids)} report(s) traités")


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser(description="Reparse reports (tops + gear) depuis uploads/uploaded et/ou LogsDir.")
    parser.add_argument("--source", choices=["uploaded", "logs", "both"], default="both",
                        help="Source des report_ids (défaut: both)")
    parser.add_argument("--only-top", action="store_true", help="Ne traiter que TOP (pas de Gear)")
    parser.add_argument("--only-gear", action="store_true", help="Ne traiter que Gear (pas de TOP)")
    parser.add_argument("--server", action="append",
                        help="Filtrer sur un serveur (option répétable). Exemple: --server Lordaeron")
    parser.add_argument("--limit", type=int, default=None, help="Limiter le nombre de reports traités")
    parser.add_argument("--workers", type=int, default=1, help="(Réservé) Nombre de workers pour étapes parallélisables")
    parser.add_argument("--dry-run", action="store_true", help="Lister ce qui serait traité, sans exécuter")
    args = parser.parse_args()

    # log entête / pied
    start = perf_counter()
    LOGGER.debug(f"{get_ms_str(start)} | reparse_all start")

    try:
        run(args.server, args.limit, args.only_top, args.only_gear, args.workers, args.source, args.dry_run)
    except Exception:
        LOGGER.exception("reparse_all | erreur inattendue")
    finally:
        LOGGER.debug(f"{get_ms_str(start)} | reparse_all finish")


if __name__ == "__main__":
    main()

