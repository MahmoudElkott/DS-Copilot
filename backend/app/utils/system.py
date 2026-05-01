# backend/app/utils/system.py
import os
import shutil
import subprocess
import re
import logging
from app.models.schemas import PythonInterpreterInfo

logger = logging.getLogger(__name__)

def discover_python_interpreters() -> list[PythonInterpreterInfo]:
    """Find Python executables available on the host machine."""
    candidates: set[str] = set()

    # Common command resolution.
    for cmd in ("python", "python3", "py"):
        resolved = shutil.which(cmd)
        if resolved:
            candidates.add(os.path.abspath(resolved))

    if os.name == "nt":
        try:
            where_proc = subprocess.run(
                ["where", "python"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            for line in where_proc.stdout.splitlines():
                path = line.strip().strip('"')
                if path and os.path.exists(path):
                    candidates.add(os.path.abspath(path))
        except Exception:  # noqa: BLE001
            logger.debug("Unable to query 'where python'", exc_info=True)

        try:
            py_launcher = subprocess.run(
                ["py", "-0p"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            for line in py_launcher.stdout.splitlines():
                match = re.search(r"([A-Za-z]:\\[^\s]+python\.exe)", line)
                if match:
                    launcher_path = match.group(1).strip().strip('"')
                    if os.path.exists(launcher_path):
                        candidates.add(os.path.abspath(launcher_path))
        except Exception:  # noqa: BLE001
            logger.debug("Unable to query 'py -0p'", exc_info=True)

    interpreters: list[PythonInterpreterInfo] = []
    default_python = shutil.which("python")
    default_python = os.path.abspath(default_python) if default_python else ""

    for path in sorted(candidates):
        try:
            version_proc = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=4,
            )
            version = (
                version_proc.stdout.strip()
                or version_proc.stderr.strip()
                or "Unknown"
            )
        except Exception:  # noqa: BLE001
            version = "Unknown"

        interpreters.append(
            PythonInterpreterInfo(
                path=path,
                version=version,
                is_default=(path == default_python),
            )
        )

    return interpreters
