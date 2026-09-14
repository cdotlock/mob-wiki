"""Markdown-aware wiki links shared by the viewer and structural checks."""

from html.parser import HTMLParser
from urllib.parse import quote
from xml.etree.ElementTree import Element

import markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor


def link_parts(value):
    target, _, label = value.partition("|")
    page, _, anchor = target.partition("#")
    return page.strip().removesuffix(".md"), anchor, label or target.split("/")[-1]


class WikiLinkProcessor(InlineProcessor):
    def handleMatch(self, match, data):
        page, anchor, label = link_parts(match.group(1))
        href = "/wiki/" + quote(page, safe="/") + ".md" if page else ""
        if anchor:
            href += "#" + quote(anchor, safe="-_")
        element = Element("a", href=href, **{"data-wikilink": page})
        element.text = label
        return element, match.start(0), match.end(0)


class WikiLinks(Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(
            WikiLinkProcessor(r"\[\[([^\]\n]+)\]\]", md), "wikilink", 175
        )


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "data-wikilink" in attrs:
            self.links.append(attrs["data-wikilink"])


def wiki_targets(content):
    collector = LinkCollector()
    collector.feed(
        markdown.markdown(content, extensions=["fenced_code", "tables", WikiLinks()])
    )
    return collector.links
