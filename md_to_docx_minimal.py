from __future__ import annotations

import argparse
import re
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")
SIZE_BY_LEVEL = {1: 32, 2: 28, 3: 24, 4: 22}


def make_run(text: str, *, bold: bool = False, code: bool = False) -> str:
    if not text:
        return ""

    props = []
    if bold:
        props.append("<w:b/>")
    if code:
        props.append('<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/>')

    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def parse_inline(text: str) -> str:
    runs: list[str] = []
    pos = 0

    for match in INLINE_RE.finditer(text):
        if match.start() > pos:
            runs.append(make_run(text[pos:match.start()]))

        token = match.group(0)
        if token.startswith("**") and token.endswith("**"):
            runs.append(make_run(token[2:-2], bold=True))
        elif token.startswith("`") and token.endswith("`"):
            runs.append(make_run(token[1:-1], code=True))
        else:
            runs.append(make_run(token))

        pos = match.end()

    if pos < len(text):
        runs.append(make_run(text[pos:]))

    return "".join(runs) or make_run("")


def make_paragraph(text: str, *, heading_level: int | None = None, code: bool = False) -> str:
    if heading_level is not None:
        size = SIZE_BY_LEVEL.get(heading_level, 22)
        return (
            "<w:p>"
            "<w:pPr><w:spacing w:before=\"240\" w:after=\"120\"/></w:pPr>"
            "<w:r><w:rPr><w:b/>"
            f"<w:sz w:val=\"{size}\"/><w:szCs w:val=\"{size}\"/>"
            "</w:rPr>"
            f"<w:t xml:space=\"preserve\">{escape(text)}</w:t>"
            "</w:r></w:p>"
        )

    runs = make_run(text, code=True) if code else parse_inline(text)
    return f"<w:p>{runs}</w:p>"


def markdown_to_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    normal_buffer: list[str] = []
    code_buffer: list[str] = []
    in_code = False

    def flush_normal() -> None:
        if normal_buffer:
            paragraphs.append(make_paragraph(" ".join(normal_buffer).strip()))
            normal_buffer.clear()

    def flush_code() -> None:
        if code_buffer:
            for line in code_buffer:
                paragraphs.append(make_paragraph(line, code=True))
            code_buffer.clear()

    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        if stripped.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_normal()
                in_code = True
            continue

        if in_code:
            code_buffer.append(raw_line)
            continue

        if not stripped:
            flush_normal()
            continue

        if stripped.startswith("#"):
            flush_normal()
            level = len(stripped) - len(stripped.lstrip("#"))
            paragraphs.append(make_paragraph(stripped[level:].strip(), heading_level=level))
            continue

        if stripped.startswith("- "):
            flush_normal()
            paragraphs.append(make_paragraph("• " + stripped[2:]))
            continue

        if re.match(r"^\d+\.\s", stripped):
            flush_normal()
            paragraphs.append(make_paragraph(stripped))
            continue

        normal_buffer.append(stripped)

    flush_normal()
    flush_code()
    return paragraphs


def write_docx(source: Path, output: Path) -> None:
    body = "".join(markdown_to_paragraphs(source.read_text(encoding="utf-8")))
    body += (
        "<w:sectPr>"
        "<w:pgSz w:w=\"12240\" w:h=\"15840\"/>"
        "<w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" "
        "w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/>"
        "</w:sectPr>"
    )

    document_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
        f"<w:body>{body}</w:body>"
        "</w:document>"
    )

    content_types = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
        "<Default Extension=\"rels\" "
        "ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        "<Override PartName=\"/word/document.xml\" "
        "ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>"
        "</Types>"
    )

    rels = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" "
        "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" "
        "Target=\"word/document.xml\"/>"
        "</Relationships>"
    )

    with ZipFile(output, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output)
    write_docx(source, output)
    print(output)


if __name__ == "__main__":
    main()
