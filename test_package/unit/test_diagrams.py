"""Tests for diagram rendering module."""

from unittest.mock import patch


from mdfluence.diagrams import render_mermaid, render_plantuml
from mdfluence.document import parse_page


class TestRenderMermaid:
    def test_mmdc_not_found(self):
        with patch("shutil.which", return_value=None):
            result = render_mermaid("graph TD; A-->B;")
            assert result is None

    def test_mmdc_success(self, tmp_path):
        png_bytes = b"\x89PNG\r\n\x1a\n fake png"

        def fake_run(cmd, **kwargs):
            # Write fake PNG to output path
            output_path = cmd[cmd.index("-o") + 1]
            with open(output_path, "wb") as f:
                f.write(png_bytes)

        with patch("subprocess.run", side_effect=fake_run):
            result = render_mermaid("graph TD; A-->B;", mmdc_path="/usr/bin/mmdc")
            assert result == png_bytes

    def test_mmdc_failure(self):
        import subprocess

        with patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "mmdc"),
        ):
            result = render_mermaid("bad", mmdc_path="/usr/bin/mmdc")
            assert result is None


class TestRenderPlantuml:
    def test_plantuml_not_found(self):
        with patch("shutil.which", return_value=None):
            result = render_plantuml("@startuml\nA -> B\n@enduml")
            assert result is None

    def test_plantuml_success(self):
        png_bytes = b"\x89PNG\r\n\x1a\n fake plantuml"

        def fake_run(cmd, **kwargs):
            # plantuml creates input.png next to input.puml
            import pathlib

            input_path = pathlib.Path(cmd[-1])
            output_path = input_path.with_suffix(".png")
            output_path.write_bytes(png_bytes)

        with patch("subprocess.run", side_effect=fake_run):
            result = render_plantuml(
                "@startuml\nA -> B\n@enduml", plantuml_path="/usr/bin/plantuml"
            )
            assert result == png_bytes


class TestDiagramIntegration:
    def test_mermaid_renders_to_image(self):
        """When render_diagrams=True and mmdc works, mermaid block becomes image."""
        png_bytes = b"\x89PNG fake"
        md = "```mermaid\ngraph TD; A-->B;\n```\n"

        with patch("mdfluence.diagrams.render_mermaid", return_value=png_bytes):
            page = parse_page(list(md), render_diagrams=True)
            assert "ac:image" in page.body
            assert len(page.attachments) == 1

    def test_mermaid_fallback_to_code(self):
        """When render_diagrams=True but mmdc fails, falls back to code block."""
        md = "```mermaid\ngraph TD; A-->B;\n```\n"

        with patch("mdfluence.diagrams.render_mermaid", return_value=None):
            page = parse_page(list(md), render_diagrams=True)
            assert "ac:structured-macro" in page.body
            assert "mermaid" in page.body

    def test_no_render_without_flag(self):
        """Without render_diagrams, mermaid renders as code block."""
        md = "```mermaid\ngraph TD; A-->B;\n```\n"
        page = parse_page(list(md), render_diagrams=False)
        assert "ac:structured-macro" in page.body
        assert "ac:image" not in page.body
