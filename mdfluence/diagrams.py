"""Render diagram code blocks (mermaid, plantuml) to images via local tools."""

from __future__ import annotations

import atexit
import logging
import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Temp dirs holding rendered diagram PNGs. They must outlive rendering so the
# upload step can read them, so they are cleaned up once at process exit.
_diagram_tempdirs: list[str] = []


@atexit.register
def _cleanup_diagram_tempdirs() -> None:
    while _diagram_tempdirs:
        shutil.rmtree(_diagram_tempdirs.pop(), ignore_errors=True)


def render_mermaid(code: str, mmdc_path: str | None = None) -> bytes | None:
    """Render mermaid code to PNG bytes using mmdc (mermaid-cli).

    Returns PNG bytes on success, None if mmdc is not available or rendering fails.
    """
    cmd = mmdc_path or shutil.which("mmdc")
    if cmd is None:
        logger.warning("mmdc not found; skipping mermaid rendering")
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.mmd"
        output_path = Path(tmpdir) / "output.png"
        input_path.write_text(code, encoding="utf-8")

        try:
            subprocess.run(  # nosec B603
                [cmd, "-i", str(input_path), "-o", str(output_path), "-q"],
                check=True,
                capture_output=True,
                timeout=30,
            )
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ) as e:
            logger.warning("mermaid rendering failed: %s", e)
            return None

        if output_path.exists():
            return output_path.read_bytes()
        return None


def write_diagram_png(png_data: bytes, filename: str) -> Path:
    """Persist rendered diagram PNG bytes to a temp file and return its path.

    Filesystem persistence for rendered diagrams lives here alongside the rest
    of the diagram tooling so the Confluence renderer stays a pure markup
    transformer and never touches the filesystem. The backing temp dir is
    tracked for cleanup at process exit (see ``_cleanup_diagram_tempdirs``).
    """
    tmpdir = tempfile.mkdtemp(prefix="mdfluence-diagram-")
    _diagram_tempdirs.append(tmpdir)
    filepath = Path(tmpdir) / filename
    filepath.write_bytes(png_data)
    return filepath


def render_plantuml(code: str, plantuml_path: str | None = None) -> bytes | None:
    """Render PlantUML code to PNG bytes using plantuml JAR or CLI.

    Returns PNG bytes on success, None if plantuml is not available or rendering fails.
    """
    cmd = plantuml_path or shutil.which("plantuml")
    if cmd is None:
        logger.warning("plantuml not found; skipping plantuml rendering")
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.puml"
        output_path = Path(tmpdir) / "input.png"
        input_path.write_text(code, encoding="utf-8")

        try:
            subprocess.run(  # nosec B603
                [cmd, "-tpng", str(input_path)],
                check=True,
                capture_output=True,
                timeout=60,
            )
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ) as e:
            logger.warning("plantuml rendering failed: %s", e)
            return None

        if output_path.exists():
            return output_path.read_bytes()
        return None
