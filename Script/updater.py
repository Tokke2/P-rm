# Fil: Script/updater.py — Filjämförande uppdaterare (REQ-K4, AGENTS.md §3)
#
# Så fungerar uppdateraren:
#   1. Hämtar senaste Latest-release från api.github.com.
#   2. Vägrar releaser som pekar på 'main' (§1: jobba aldrig emot main).
#   3. Jämför filer (relativ sökväg + sha256) mot appens filer.
#   4. Backar upp varje fil som ska ändras/raderas till Uppdatering_backup/.
#   5. Applicera ENDAST skillnaden (ändra/lägg till/radera).
#   6. Verifierar: filuppsättningen + hasharna ska exakt matcha releasen.
#   7. Verifiering OK → backup raderas. Verifiering FEL → full rollback.
#
# Driftnotis (§2): asset-uppladdning är blockad i sandlådan →
# jämförelsekällan är releasens auto-genererade källarkiv via
# codeload.github.com. Inga externa beroenden (urllib + tarfile).
#
# BOOTSTRAP: modulen importerar INTE tkinter och kan köras fristående —
#   python Script/updater.py
# (används om själva appen inte kan starta, t.ex. vid GUI-bugg.)

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import threading
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO = "Tokke2/P-rm"
API_BASE = "https://api.github.com"
CODELOAD_BASE = "https://codeload.github.com"
USER_AGENT = "Parmetikett-Updater (REQ-K4; filjämförelse mot Latest-release)"

APP_ROOT = Path(__file__).resolve().parent.parent
VERSION_PATH = APP_ROOT / "VERSION.txt"
BACKUP_DIR = APP_ROOT / "Uppdatering_backup"

# Kataloger/filer som ALDRIG rörs av uppdateraren (användardata/runtime).
SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv",
    "Loggar", "Logotyp", "Profiler", "export",
    "Uppdatering_backup",
}
SKIP_FILES = {"settings.json"}

INFO_TIMEOUT = 15
DOWNLOAD_TIMEOUT = 120

# Auto-uppdatering 00:00 varje dag: missad midnatt catchas upp om appen
# startar inom denna fönstertid efter midnatt.
CATCHUP_WINDOW_MIN = 5

_UPDATE_LOCK = threading.Lock()  # serialiserar auto + manuell uppdatering


class UpdaterError(Exception):
    """Uppdateringen avbröts (loggas som UPD_* fel i loggsystemet)."""


# ──────────────────────────────────────────────────────────
# VERSION
# ──────────────────────────────────────────────────────────

def read_installed_version(version_path: Path = VERSION_PATH) -> str:
    """Läser installerad version ('1.2.0'); saknas filen → '0.0.0'."""
    try:
        text = version_path.read_text(encoding="utf-8").strip()
        return text or "0.0.0"
    except OSError:
        return "0.0.0"


def parse_version(version: str) -> Tuple[int, ...]:
    """'v1.2.0' / '1.2.0' → (1, 2, 0). Ogiltigt → (0, 0, 0)."""
    cleaned = str(version or "").strip().lower().lstrip("v")
    parts = cleaned.split(".")
    numbers: List[int] = []
    for part in parts[:3]:
        digits = "".join(char for char in part if char.isdigit())
        numbers.append(int(digits) if digits else 0)
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)


def is_newer_release(release_tag: str, installed: str) -> bool:
    """True om release-taggen är nyare än installerad version."""
    return parse_version(release_tag) > parse_version(installed)


# ──────────────────────────────────────────────────────────
# NÄTVERK (injectable för tester — testerna använder aldrig nätet)
# ──────────────────────────────────────────────────────────

def _http_get_bytes(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def get_latest_release_info(repo: str = REPO) -> Dict[str, str]:
    """Hämtar senaste Latest-release: {tag, name, target_commitish}."""
    raw = _http_get_bytes(f"{API_BASE}/repos/{repo}/releases/latest", INFO_TIMEOUT)
    data = json.loads(raw.decode("utf-8"))
    return {
        "tag": str(data.get("tag_name", "")),
        "name": str(data.get("name", "")),
        "target_commitish": str(data.get("target_commitish", "")),
    }


def download_release_archive(
    tag: str, dest_dir: Path, repo: str = REPO
) -> Path:
    """Laddar ner release-källarkivet (tar.gz) via codeload.github.com."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    url = f"{CODELOAD_BASE}/{repo}/tar.gz/refs/tags/{tag}"
    dest = dest_dir / f"release_{tag.lstrip('v')}.tar.gz"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
        with dest.open("wb") as handle:
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    if not dest.is_file() or dest.stat().st_size == 0:
        raise UpdaterError(f"Nedladdat arkiv är tomt: {dest}")
    return dest


# ──────────────────────────────────────────────────────────
# ARKIV & HASH
# ──────────────────────────────────────────────────────────

def extract_archive(tar_gz: Path, dest_dir: Path) -> Path:
    """Extraherar tar.gz säkert och returnerar arkivets innerrot-mapp."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_gz, "r:gz") as tar:
        try:
            tar.extractall(dest_dir, filter="data")
        except TypeError:  # äldre Python utan filter-parameter
            tar.extractall(dest_dir)
    subdirs = [item for item in dest_dir.iterdir() if item.is_dir()]
    if len(subdirs) == 1:
        return subdirs[0]
    return dest_dir


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(128 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_file_hashes(root: Path) -> Dict[str, str]:
    """sha256 för alla hanterade filer (relativ posix-sökväg → hash).

    Användardata (SKIP_DIRS/SKIP_FILES) inkluderas aldrig.
    """
    root = Path(root)
    hashes: Dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.name in SKIP_FILES:
            continue
        hashes[rel.as_posix()] = _hash_file(path)
    return hashes


def compare_files(
    current_root: Path, release_root: Path
) -> Dict[str, List[str]]:
    """Skillnaden mellan appen och releasen (REQ-K4: filnamn + innehåll).

    Returnerar {to_update, to_add, to_remove, unchanged} — endast
    hanterade filer (användardata hoppas över).
    """
    current = build_file_hashes(current_root)
    release = build_file_hashes(release_root)
    to_update = sorted(
        rel for rel, sha in release.items()
        if rel in current and current[rel] != sha
    )
    to_add = sorted(rel for rel in release if rel not in current)
    to_remove = sorted(rel for rel in current if rel not in release)
    unchanged = sorted(
        rel for rel, sha in release.items()
        if rel in current and current[rel] == sha
    )
    return {
        "to_update": to_update,
        "to_add": to_add,
        "to_remove": to_remove,
        "unchanged": unchanged,
    }


# ──────────────────────────────────────────────────────────
# APPLICERA + VERIFIERA + BACKUP
# ──────────────────────────────────────────────────────────

def _backup_files(current_root: Path, relpaths: List[str]) -> int:
    """Kopierar filer som ska ändras/raderas till backupmappen."""
    count = 0
    for rel in relpaths:
        source = current_root / rel
        if not source.is_file():
            continue
        dest = BACKUP_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        count += 1
    return count


def _remove_backup_dir() -> None:
    """Tar bort backupmappen (anropas ENDAST efter lyckad verifiering)."""
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR, ignore_errors=True)


def _cleanup_inactive_files(root: Path) -> List[str]:
    """Rensar INAKTIVA filer/rester efter en uppdatering (användarönskemål).

    • __pycache__-mappar och *.pyc/*.pyo (bytecode — regenereras alltid)
    • överblivna *.tmp (t.ex. halvskriven settings.json.tmp)
    • tomma mappar (t.ex. en mapp som blev tom när alla dess filer
      raderades som to_remove) — men ALDRIG skyddade mappar (SKIP_DIRS:
      Loggar/Logotyp/Profiler/export/Uppdatering_backup/.git/venv …)

    Användardata pekas aldrig på: rensningen går bara åt filtyper som
    inte ingår i hash-jämförelsen, och tomma-mapp-städningen hoppar över
    SKIP_DIRS. Returnerar lista med relativta sökvägar som togs bort.
    """
    removed: List[str] = []
    root = Path(root)
    if not root.is_dir():
        return removed

    def _protected(path: Path) -> bool:
        # __pycache__ är skippat i HASH-jämförelsen men ska ändå STÄDAS
        # (inaktiv bytecode) — det är därför det inte skyddas här.
        rel = path.relative_to(root)
        return any(
            part in SKIP_DIRS and part != "__pycache__"
            for part in rel.parts
        )

    # 1) __pycache__ + bytecode
    for cache_dir in sorted(root.rglob("__pycache__")):
        if _protected(cache_dir):
            continue
        shutil.rmtree(cache_dir, ignore_errors=True)
        removed.append(cache_dir.relative_to(root).as_posix())
    for pattern in ("*.pyc", "*.pyo", "*.tmp"):
        for stray in root.rglob(pattern):
            if _protected(stray) or not stray.is_file():
                continue
            try:
                stray.unlink()
                removed.append(stray.relative_to(root).as_posix())
            except OSError:
                pass

    # 2) tomma mappar (innerst först) — skippar skyddade + roten själv
    for dirpath in sorted(
        (p for p in root.rglob("*") if p.is_dir()), reverse=True
    ):
        if dirpath == root or _protected(dirpath):
            continue
        try:
            next(dirpath.iterdir())          # har innehåll → ok
        except StopIteration:
            try:
                dirpath.rmdir()
                removed.append(dirpath.relative_to(root).as_posix())
            except OSError:
                pass
        except OSError:
            pass
    return removed


# Publikt alias (API) — se _cleanup_inactive_files för dokumentationen.
cleanup_inactive_files = _cleanup_inactive_files


def apply_update(
    current_root: Path,
    release_root: Path,
    diff: Dict[str, List[str]],
) -> Dict[str, Any]:
    """Applicera skillnaden med backup → verifiera → ta bort backup vid OK.

    Följer REQ-K4: backup tas bort FÖRST när uppdateringen verifierats
    som lyckad. Vid verifieringsfel rullas allt tillbaka.
    """
    current_root = Path(current_root)
    release_root = Path(release_root)

    changed = list(diff["to_update"]) + list(diff["to_remove"])
    backed_up = _backup_files(current_root, changed)

    # 1) Applicera: ändra/lägg till.
    copied = 0
    for rel in list(diff["to_update"]) + list(diff["to_add"]):
        source = release_root / rel
        dest = current_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        copied += 1
    # 2) Applicera: radera utgångna filer.
    removed = 0
    for rel in diff["to_remove"]:
        target = current_root / rel
        if target.is_file():
            target.unlink()
            removed += 1

    # 3) Verifiera — filuppsättning + hash ska exakt matcha releasen.
    verified = build_file_hashes(current_root) == build_file_hashes(release_root)
    if not verified:
        # ROLLBACK: återställ ändrade/raderade, ta bort tillagda.
        for rel in list(diff["to_update"]) + list(diff["to_remove"]):
            backup_file = BACKUP_DIR / rel
            target = current_root / rel
            if backup_file.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, target)
            elif rel in diff["to_remove"] and target.is_file():
                target.unlink()
        for rel in diff["to_add"]:
            target = current_root / rel
            if target.is_file():
                target.unlink()
        _remove_backup_dir()
        return {
            "ok": False, "verified": False,
            "fel": "Verifiering misslyckades — rollback genomförd.",
            "backed_up": backed_up, "copied": copied, "removed": removed,
        }

    # 4) Lyckad verifiering → nu (och först nu) tas backupen bort.
    _remove_backup_dir()
    cleaned = _cleanup_inactive_files(current_root)
    return {
        "ok": True, "verified": True,
        "copied": copied, "removed": removed,
        "unchanged": len(diff["unchanged"]),
        "städade": len(cleaned),
        "backup_removed": True,
    }


# ──────────────────────────────────────────────────────────
# ORKESTRERING
# ──────────────────────────────────────────────────────────

def next_midnight_delay(
    now: Optional[datetime] = None,
    catchup_minutes: int = CATCHUP_WINDOW_MIN,
) -> int:
    """Millisekunder till nästa 00:00 (för auto-uppdateringsschemat).

    Startar appen inom *catchup_minutes* efter midnatt returneras 0 —
    den missade körningen utförs då direkt (uppcatchning). Pure funktion
    (injicera `now`) så den kan testas utan verklig klocka.
    """
    now = now or datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    since_midnight = (now - midnight).total_seconds()
    if since_midnight <= catchup_minutes * 60:
        return 0
    next_midnight = midnight + timedelta(days=1)
    return int((next_midnight - now).total_seconds() * 1000)


def auto_update(
    current_root: Path = APP_ROOT,
    log: Any = None,
    fetch_info: Optional[Callable[[], Dict[str, str]]] = None,
    download_archive: Optional[Callable[[str, Path], Path]] = None,
) -> Dict[str, Any]:
    """Tyst auto-uppdatering (00:00-schemaläggarens anrop).

    Samma flöde som run_update men ALDRIG några dialoger — allting
    loggas i loggsystemet (applog vid lyckat/ingenting, fellog vid fel).
    """
    if log is None:
        try:
            from Script import loggar as _loggar
        except ImportError:
            import loggar as _loggar  # type: ignore[no-redef]
        log = _loggar.logg
    log.log_app("AUTO-UPD: schemalagd uppdatering (00:00) startar")
    try:
        result = run_update(
            current_root,
            fetch_info=fetch_info,
            download_archive=download_archive,
            log=log,
        )
    except Exception as exc:
        log.log_error("UPD_AUTO", f"Auto-uppdatering kraschade: {exc}")
        return {"ok": False, "steg": "auto", "fel": str(exc)}
    if result.get("ok") and result.get("uppdaterad"):
        log.log_app(
            f"AUTO-UPD: uppdaterade till {result.get('tag')} — "
            "starta om appen för att ändringarna ska gälla"
        )
    elif result.get("ok"):
        log.log_app("AUTO-UPD: ingen uppdatering behövs")
    else:
        log.log_error(
            "UPD_AUTO", f"Auto-uppdatering misslyckades: {result.get('fel')}"
        )
    return result

def check_for_new_release(
    fetch_info: Optional[Callable[[], Dict[str, str]]] = None,
    version_path: Path = VERSION_PATH,
) -> Dict[str, Any]:
    """Lättviktig kontroll: finns en nyare Latest-release? (ingen nedladdning)"""
    fetch = fetch_info or get_latest_release_info
    info = fetch()
    target = info.get("target_commitish", "")
    if target == "main":
        raise UpdaterError(
            "Latest-releasen pekar på 'main' — förbjudet enligt §1. Avbryter."
        )
    installed = read_installed_version(version_path)
    tag = info.get("tag", "")
    return {
        "ny_release": is_newer_release(tag, installed),
        "tag": tag,
        "installed": installed,
        "target_commitish": target,
    }


def run_update(
    current_root: Path = APP_ROOT,
    *,
    fetch_info: Optional[Callable[[], Dict[str, str]]] = None,
    download_archive: Optional[Callable[[str, Path], Path]] = None,
    log: Any = None,
) -> Dict[str, Any]:
    """Full uppdatering: jämför → backup → applicera → verifiera → städa.

    `fetch_info`/`download_archive` kan injiceras i tester (offline).
    `log` är en LogManager (standard: Script.loggar.logg).
    """
    with _UPDATE_LOCK:  # auto + manuell ska aldrig köras samtidigt
        return _run_update_locked(
            current_root,
            fetch_info=fetch_info,
            download_archive=download_archive,
            log=log,
        )


def _run_update_locked(
    current_root: Path,
    *,
    fetch_info: Optional[Callable[[], Dict[str, str]]] = None,
    download_archive: Optional[Callable[[str, Path], Path]] = None,
    log: Any = None,
) -> Dict[str, Any]:
    if log is None:
        try:
            from Script import loggar as _loggar
        except ImportError:
            import loggar as _loggar  # type: ignore[no-redef]
        log = _loggar.logg

    def _fel(kod: str, meddelande: str) -> None:
        try:
            log.log_error(kod, meddelande)
        except Exception:
            print(f"[Updater] {kod}: {meddelande}")

    current_root = Path(current_root)
    log.log_app("Uppdatering startad (REQ-K4: filjämförelse mot Latest)")

    try:
        info = (fetch_info or get_latest_release_info)()
    except Exception as exc:
        _fel("UPD_CHECK", f"Kunde inte hämta Latest-release: {exc}")
        return {"ok": False, "steg": "check", "fel": str(exc)}

    tag = info.get("tag", "")
    target = info.get("target_commitish", "")
    if target == "main" or not target:
        _fel(
            "UPD_CHECK",
            f"Release {tag} pekar på {target!r} (main/okänt) — avbryter (§1).",
        )
        return {
            "ok": False, "steg": "check",
            "fel": f"Releasen pekar på {target!r} — main är förbjudet (§1).",
        }

    installed = read_installed_version(current_root / "VERSION.txt")
    if not is_newer_release(tag, installed):
        log.log_app(f"Redan senaste version ({installed} = {tag})")
        return {
            "ok": True, "steg": "check", "uppdaterad": False,
            "tag": tag, "installed": installed,
            "meddelande": f"Redan senaste versionen ({installed}).",
        }

    temp_dir = Path(tempfile.mkdtemp(prefix="parm_upd_"))
    try:
        try:
            archive = (download_archive or download_release_archive)(tag, temp_dir)
            release_root = extract_archive(archive, temp_dir / "ut")
        except Exception as exc:
            _fel("UPD_DOWNLOAD", f"Nedladdning/utpackning misslyckades: {exc}")
            return {"ok": False, "steg": "download", "fel": str(exc), "tag": tag}

        diff = compare_files(current_root, release_root)
        log.log_app(
            f"Jämförelse mot {tag}: {len(diff['to_update'])} ändrade, "
            f"{len(diff['to_add'])} nya, {len(diff['to_remove'])} borttagna, "
            f"{len(diff['unchanged'])} oförändrade"
        )

        result = apply_update(current_root, release_root, diff)
        if result.get("ok"):
            log.resolve_error("UPD_DOWNLOAD")
            log.resolve_error("UPD_APPLY")
            log.resolve_error("UPD_VERIFY")
            log.log_app(
                f"Uppdatering till {tag} klar: {result.get('copied')} filer "
                f"uppdaterade, {result.get('removed')} raderade, "
                f"{result.get('städade', 0)} inaktiva städade, "
                f"verifierad OK, backup borttagen"
            )
            result.update({"tag": tag, "steg": "klar", "uppdaterad": True})
        else:
            _fel("UPD_VERIFY", str(result.get("fel", "Verifiering misslyckades")))
            result.update({"tag": tag, "steg": "verify"})
        return result
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


__all__ = [
    "REPO", "API_BASE", "CODELOAD_BASE", "APP_ROOT", "VERSION_PATH",
    "BACKUP_DIR", "SKIP_DIRS", "SKIP_FILES",
    "UpdaterError",
    "read_installed_version", "parse_version", "is_newer_release",
    "get_latest_release_info", "download_release_archive",
    "extract_archive", "build_file_hashes", "compare_files",
    "apply_update", "check_for_new_release", "run_update",
    "cleanup_inactive_files",
    "next_midnight_delay", "auto_update", "CATCHUP_WINDOW_MIN",
]


if __name__ == "__main__":  # BOOTSTRAP: kör uppdateraren utan GUI
    _result = run_update()
    print(json.dumps(_result, ensure_ascii=False, indent=2))
    sys.exit(0 if _result.get("ok") else 1)
