"""Ingestion: raw sacred-texts HTML -> clean, metadata-tagged paragraphs.

Parser: BeautifulSoup (bs4) with Python's built-in `html.parser` backend.
Raw HTML in data/raw/ is never modified; this module only reads it.

Page anatomy (verified on a few pages, NOT yet on all 237):
  <article data-slot="reader-content">
    <h1>SECTION III</h1>
    <p>(Paushya Parva)</p>          <- sub-parva label
    <p>Sauti said, "...</p>         <- story paragraph (bare <p>)
    <p><a>p. 33</a></p>             <- printed-page marker
  </article>
Everything outside the <article> (head, scripts, sidebar, footer) is ignored.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

PAGE_MARKER = re.compile(r"^p\.\s*(\d+|[ivxlc]+)$", re.I)  # preface uses roman: "p. xii"
SECTION_HEADING = re.compile(r"^SECTION [IVXLC]+$")
SUB_PARVA = re.compile(r"^\((.+)\)$")


@dataclass
class Paragraph:
    file: str                  # source file name, e.g. section_003.html
    heading: str               # raw <h1> text, e.g. "SECTION III"
    sub_parva: str | None      # e.g. "Paushya Parva" (None if not seen yet)
    para_index: int            # position among story paragraphs in this file
    printed_page: int | str | None  # most recent "p. NN" marker seen BEFORE this paragraph
    text: str


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_file(path: Path) -> list[Paragraph]:
    # The files are UTF-8; reading them as latin-1 turns ' and – into mojibake.
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    article = soup.find("article", attrs={"data-slot": "reader-content"})
    if article is None:
        raise ValueError(f"{path.name}: no reader-content <article> found")

    # Usually the <h1> is "SECTION III", but on file 002 the <h1> is just the book title
    # and "SECTION I" sits in a <div>. So look for a SECTION heading anywhere, else use <h1>.
    heading = ""
    for el in article.find_all(["h1", "h2", "h3", "div"]):
        t = _clean(el.get_text())
        if SECTION_HEADING.match(t):
            heading = t
            break
    if not heading:
        h1 = article.find("h1")
        heading = _clean(h1.get_text()) if h1 else ""

    paragraphs: list[Paragraph] = []
    sub_parva: str | None = None
    printed_page: int | str | None = None

    # TODO(me): this loop is the cleaning rule set. Right now it is my first draft;
    # after we review the output on the first 2 files, decide what to keep/drop/change.
    for p in article.find_all("p"):
        text = _clean(p.get_text(" "))
        if not text:
            continue
        if m := PAGE_MARKER.match(text):
            v = m.group(1)
            printed_page = int(v) if v.isdigit() else v
            continue
        if m := SUB_PARVA.match(text):
            sub_parva = m.group(1)
            continue
        paragraphs.append(
            Paragraph(path.name, heading, sub_parva, len(paragraphs), printed_page, text)
        )
    return paragraphs
