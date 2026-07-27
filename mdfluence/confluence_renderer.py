import re
import uuid
from html.parser import HTMLParser
from pathlib import Path
from typing import List, NamedTuple
from urllib.parse import unquote, urlparse

import mistune

from mdfluence import diagrams
from mdfluence.anchor import _heading_to_markdown_anchor
from mdfluence.plugins.alerts import ALERT_TYPE_MAP

_VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


class _XHTMLConverter(HTMLParser):
    """Convert HTML to XHTML by self-closing void elements."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attr_str = "".join(
            f' {k}="{v}"' if v is not None else f" {k}" for k, v in attrs
        )
        if tag in _VOID_ELEMENTS:
            self._parts.append(f"<{tag}{attr_str} />")
        else:
            self._parts.append(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag):
        if tag not in _VOID_ELEMENTS:
            self._parts.append(f"</{tag}>")

    def handle_data(self, data):
        self._parts.append(data)

    def handle_entityref(self, name):
        self._parts.append(f"&{name};")

    def handle_charref(self, name):
        self._parts.append(f"&#{name};")

    def handle_comment(self, data):
        self._parts.append(f"<!--{data}-->")

    def handle_pi(self, data):
        self._parts.append(f"<?{data}>")

    def convert(self, html: str) -> str:
        self._parts = []
        self.feed(html)
        return "".join(self._parts)


_xhtml_converter = _XHTMLConverter()


class RelativeLink(NamedTuple):
    path: str
    fragment: str
    replacement: str
    original: str
    escaped_original: str


class ConfluenceTag(object):
    def __init__(self, name, text="", attrib=None, namespace="ac", cdata=False):
        self.name = name
        self.text = text
        self.namespace = namespace
        if attrib is None:
            attrib = {}
        self.attrib = attrib
        self.children = []
        self.cdata = cdata

    def render(self):
        namespaced_name = self.add_namespace(self.name, namespace=self.namespace)
        namespaced_attribs = {
            self.add_namespace(
                attribute_name, namespace=self.namespace
            ): attribute_value
            for attribute_name, attribute_value in self.attrib.items()
        }

        content = "<{}{}>{}{}</{}>".format(
            namespaced_name,
            " {}".format(
                " ".join(
                    [
                        '{}="{}"'.format(name, value)
                        for name, value in sorted(namespaced_attribs.items())
                    ]
                )
            )
            if namespaced_attribs
            else "",
            "".join([child.render() for child in self.children]),
            "<![CDATA[{}]]>".format(self.text) if self.cdata else self.text,
            namespaced_name,
        )
        return "{}\n".format(content)

    @staticmethod
    def add_namespace(tag, namespace):
        return "{}:{}".format(namespace, tag)

    def append(self, child):
        self.children.append(child)


class ConfluenceRenderer(mistune.HTMLRenderer):
    def __init__(
        self,
        strip_header=False,
        remove_text_newlines=False,
        enable_relative_links=False,
        anchor_map=None,
        render_diagrams=False,
        mmdc_path=None,
        plantuml_path=None,
        enable_line_numbers=False,
    ):
        super().__init__(escape=False)
        self.strip_header = strip_header
        self.remove_text_newlines = remove_text_newlines
        self.enable_line_numbers = enable_line_numbers
        self.attachments = list()
        self.title = None
        self.enable_relative_links = enable_relative_links
        self.relative_links: List[RelativeLink] = list()
        self._has_math = False
        self._task_id = 0
        self._anchor_map: dict = anchor_map or {}
        self._heading_counts: dict = {}
        self._anchor_map_reverse: dict = (
            {v: k for k, v in self._anchor_map.items()} if anchor_map else {}
        )
        self._diagram_counter = 0
        self.render_diagrams = render_diagrams
        self.mmdc_path = mmdc_path
        self.plantuml_path = plantuml_path

    def reinit(self):
        self.attachments = list()
        self.relative_links = list()
        self._has_math = False
        self._task_id = 0
        self._diagram_counter = 0
        self.title = None
        self._heading_counts = {}

    def heading(self, text, level, **attrs):
        if self.title is None and level == 1:
            self.title = text
            # Don't duplicate page title as a header
            if self.strip_header:
                return ""

        heading_html = super().heading(text, level, **attrs)

        if self._anchor_map:
            # Find the confluence anchor for this heading by tracking heading order.
            # Strip HTML tags to get plain text for slug computation
            plain_text = re.sub(r"<[^>]+>", "", text).strip()
            md_base = _heading_to_markdown_anchor(plain_text)
            if md_base:
                count = self._heading_counts.get(md_base, 0)
                md_anchor = md_base if count == 0 else f"{md_base}-{count}"
                self._heading_counts[md_base] = count + 1

                if md_anchor in self._anchor_map:
                    cf_anchor = self._anchor_map[md_anchor]
                    anchor_macro = self._confluence_anchor(cf_anchor)
                    heading_html = anchor_macro + heading_html

        return heading_html

    def structured_macro(self, name):
        return ConfluenceTag("structured-macro", attrib={"name": name})

    def parameter(self, name, value):
        parameter_tag = ConfluenceTag("parameter", attrib={"name": name})
        parameter_tag.text = value
        return parameter_tag

    def plain_text_body(self, text):
        body_tag = ConfluenceTag("plain-text-body", cdata=True)
        body_tag.text = text
        return body_tag

    def link(self, text, url, title=None):
        parsed_url = urlparse(url)
        if (
            self.enable_relative_links
            and (not parsed_url.scheme and not parsed_url.netloc)
            and parsed_url.path
        ):
            # relative link
            replacement_link = f"md2cf-internal-link-{uuid.uuid4()}"
            self.relative_links.append(
                RelativeLink(
                    # make sure to unquote the url as relative paths
                    # might have escape sequences
                    path=unquote(parsed_url.path),
                    replacement=replacement_link,
                    fragment=parsed_url.fragment,
                    original=url,
                    escaped_original=mistune.escape_url(url),
                )
            )
            url = replacement_link
        elif (
            self._anchor_map
            and not parsed_url.scheme
            and not parsed_url.netloc
            and not parsed_url.path
            and parsed_url.fragment
        ):
            # Local fragment link — rewrite to Confluence anchor
            fragment = parsed_url.fragment
            if fragment in self._anchor_map:
                url = f"#{self._anchor_map[fragment]}"
        return super().link(text, url, title)

    def text(self, text):
        if self.remove_text_newlines:
            text = text.replace("\n", " ")

        return super().text(text)

    def block_code(self, code, info=None):
        if self.render_diagrams and info in ("mermaid", "plantuml"):
            png_data = self._render_diagram(code, info)
            if png_data is not None:
                self._diagram_counter += 1
                filename = f"diagram-{self._diagram_counter}.png"
                # Persisting the PNG for upload is a filesystem concern owned by
                # the diagrams module, not the renderer.
                filepath = diagrams.write_diagram_png(png_data, filename)
                self.attachments.append(str(filepath))
                # Render as image attachment
                root_element = ConfluenceTag(
                    name="image", attrib={"alt": f"{info} diagram"}, namespace="ac"
                )
                url_tag = ConfluenceTag(
                    "attachment", attrib={"filename": filename}, namespace="ri"
                )
                root_element.append(url_tag)
                return root_element.render()

        root_element = self.structured_macro("code")
        if info is not None:
            lang_parameter = self.parameter(name="language", value=info)
            root_element.append(lang_parameter)
        linenumbers_value = "true" if self.enable_line_numbers else "false"
        root_element.append(self.parameter(name="linenumbers", value=linenumbers_value))
        root_element.append(self.plain_text_body(code))
        return root_element.render()

    def _render_diagram(self, code: str, diagram_type: str) -> bytes | None:
        if diagram_type == "mermaid":
            return diagrams.render_mermaid(code, mmdc_path=self.mmdc_path)
        elif diagram_type == "plantuml":
            return diagrams.render_plantuml(code, plantuml_path=self.plantuml_path)
        return None

    def image(self, text, url, title=None):
        attributes = {"alt": text}
        if title:
            attributes["title"] = title

        root_element = ConfluenceTag(name="image", attrib=attributes)
        parsed_source = urlparse(url)
        if not parsed_source.netloc:
            # Local file, requires upload
            basename = Path(url).name
            url_tag = ConfluenceTag(
                "attachment", attrib={"filename": basename}, namespace="ri"
            )
            self.attachments.append(url)
        else:
            url_tag = ConfluenceTag("url", attrib={"value": url}, namespace="ri")
        root_element.append(url_tag)

        return root_element.render()

    def task_list_item(self, text, checked=False):
        self._task_id += 1
        status = "complete" if checked else "incomplete"
        # Strip wrapping <p> tags for clean task body
        if text.startswith("<p>") and text.rstrip().endswith("</p>"):
            text = text[3:].rstrip()[:-4]
        task = ConfluenceTag("task", namespace="ac")
        task_id = ConfluenceTag("task-id", namespace="ac")
        task_id.text = str(self._task_id)
        task_status = ConfluenceTag("task-status", namespace="ac")
        task_status.text = status
        task_body = ConfluenceTag("task-body", namespace="ac")
        task_body.text = text
        task.append(task_id)
        task.append(task_status)
        task.append(task_body)
        return task.render()

    def list(self, text, ordered, **attrs):
        if "<ac:task>" in text:
            return "<ac:task-list>\n" + text + "</ac:task-list>\n"
        return super().list(text, ordered, **attrs)

    def _confluence_anchor(self, name):
        macro = self.structured_macro("anchor")
        macro.append(self.parameter("", name))
        return macro.render()

    def _confluence_anchor_link(self, anchor_name, text):
        link_tag = ConfluenceTag("link", attrib={"anchor": anchor_name})
        body_tag = ConfluenceTag("plain-text-link-body", cdata=True)
        body_tag.text = text
        link_tag.append(body_tag)
        return link_tag.render()

    def footnote_ref(self, key, index):
        i = str(index)
        anchor = self._confluence_anchor("fnref-" + i)
        link = self._confluence_anchor_link("fn-" + i, i)
        return anchor + "<sup>" + link + "</sup>"

    def footnote_item(self, text, key, index):
        i = str(index)
        anchor = self._confluence_anchor("fn-" + i)
        back = self._confluence_anchor_link("fnref-" + i, "\u21a9")
        text = text.rstrip()
        if text.endswith("</p>"):
            text = text[:-4] + back + "</p>"
        else:
            text = text + "\n" + back
        return "<li>" + anchor + text + "</li>\n"

    def footnotes(self, text):
        return '<section class="footnotes">\n<ol>\n' + text + "</ol>\n</section>\n"

    def inline_html(self, html):
        return _xhtml_converter.convert(html)

    def block_html(self, html):
        return _xhtml_converter.convert(html)

    def _enable_latex_math_macro(self):
        macro = self.structured_macro("enablelatexmath")
        macro.append(self.parameter("hide", "true"))
        return macro.render()

    def inline_math(self, text):
        self._has_math = True
        macro = self.structured_macro("mathinline")
        macro.append(self.parameter("body", text))
        return macro.render().rstrip("\n")

    def block_math(self, text):
        self._has_math = True
        root = self.structured_macro("mathblock")
        root.append(self.plain_text_body(text))
        return root.render()

    def block_alert(self, text, alert_type="NOTE"):
        macro_name = ALERT_TYPE_MAP.get(alert_type.upper(), "info")
        root = self.structured_macro(macro_name)
        body_tag = ConfluenceTag("rich-text-body", namespace="ac")
        body_tag.text = text
        root.append(body_tag)
        return root.render()

    def mark(self, text):
        return f'<span style="background-color: #ffe59a;">{text}</span>'
