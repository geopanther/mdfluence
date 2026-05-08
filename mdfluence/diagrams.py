"""Render diagram code blocks (mermaid, plantuml) to images via local tools."""

from __future__ import annotations

import logging
import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


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
