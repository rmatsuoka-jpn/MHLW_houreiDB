"""Convert one notice in the MHLW database from HTML to Markdown."""

import argparse
from datetime import datetime, timedelta, timezone
from html import escape
import json
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
from time import sleep
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

from lxml import etree, html


DOCUMENT_URL = "https://www.mhlw.go.jp/web/t_doc"
JST = timezone(timedelta(hours=9))
TABLE_TAGS = {"table", "caption", "thead", "tbody", "tfoot", "tr", "th", "td", "br"}
TABLE_ATTRIBUTES = ("rowspan", "colspan", "scope")


def page_url(notice_id, page):
    query = urlencode({"dataId": notice_id, "dataType": 1, "pageNo": page})
    return f"{DOCUMENT_URL}?{query}"


def fetch(url):
    request = Request(url, headers={"User-Agent": "MHLW_houreiDB/0.1 (notice converter)"})
    with urlopen(request, timeout=30) as response:
        if response.headers.get_content_type() != "text/html":
            raise ValueError(f"HTMLを取得できませんでした: {url}")
        return response.read().decode("utf-8")


def parse_page(source):
    return html.fromstring(source)


def page_count(document):
    totals = document.xpath("//*[@id='currentPage']/preceding-sibling::span[1]/text()")
    total = int(totals[0]) if totals else 1
    if total < 1:
        raise ValueError("通知のページ数が不正です")
    return total


def download(notice_id):
    acquired = datetime.now(JST).date().isoformat()
    first_page = fetch(page_url(notice_id, 1))
    pages = [first_page]
    for page in range(2, page_count(parse_page(first_page)) + 1):
        sleep(1)
        pages.append(fetch(page_url(notice_id, page)))
    return {"notice_id": notice_id, "acquired": acquired, "pages": pages}


def node_text(node):
    return "".join(node.itertext()).strip()


def markdown_text(value):
    return re.sub(r"([\\`*_{}\[\]<>#+.!|~$&-])", r"\\\1", value)


def markdown_link(label, url):
    return f"[{markdown_text(label)}](<{url.replace('>', '%3E')}>)"


def http_url(page, target):
    link = urljoin(page, target)
    return link if urlsplit(link).scheme in {"http", "https"} else ""


def is_attachment(node):
    return urlsplit(node.get("href", "")).path.rsplit("/", 1)[-1] == "t_img"


def render(node, url, in_table=False):
    tag = node.tag
    if not isinstance(tag, str) or tag in {"script", "style"}:
        return ""
    if tag == "tr" and node.get("class") == "fixed-colspec":
        return ""
    if tag == "img":
        if node.get("alt") == "別ウィンドウが開きます":
            return ""
        label = node.get("alt", "").strip()
        label = f"原本に画像あり（{label}）" if label else "原本に画像あり"
        if in_table:
            return f'<a href="{escape(url)}">{escape(label)}</a>'
        return markdown_link(label, url)
    if tag == "br":
        return "<br>" if in_table else "  \n"
    if tag == "a":
        target = http_url(url, node.get("href", ""))
        label = node_text(node) or "原本に画像あり"
        if is_attachment(node):
            label = f"原本に画像あり（{node_text(node)}）" if node_text(node) else label
        elif not node_text(node) and node.find(".//img") is not None:
            return render(node.find(".//img"), url, in_table)
        if target:
            if in_table:
                return f'<a href="{escape(target)}">{escape(label)}</a>'
            return markdown_link(label, target)

    in_table = in_table or tag == "table"
    encode = escape if in_table else markdown_text
    parts = [encode(node.text or "")]
    for child in node:
        parts.extend((render(child, url, in_table), encode(child.tail or "")))
    content = "".join(parts)
    if in_table and tag in TABLE_TAGS:
        attrs = "".join(
            f' {name}="{escape(node.get(name))}"'
            for name in TABLE_ATTRIBUTES if node.get(name) is not None
        )
        if tag == "table":
            content = re.sub(r"\s*\n\s*", " ", content)
            return f"\n\n<table{attrs}>{content}</table>\n\n"
        return f"<{tag}{attrs}>{content}</{tag}>"
    if in_table and tag == "p":
        return f"<p>{content}</p>"
    if not in_table and re.fullmatch(r"h[1-6]", tag):
        return f"\n\n{'#' * max(3, int(tag[1]))} {content.strip()}\n\n"
    if not in_table and tag in {"p", "div", "li"} and content.strip():
        return f"\n\n{content.strip()}\n\n"
    return content


def read_page(document, notice_id, page, total):
    url = page_url(notice_id, page)
    container = document.find(".//div[@id='contents']")
    if container is None:
        raise ValueError(f"本文の領域が見つかりません: {url}")
    identity = document.xpath("//input[@id='dataId']/@value")
    current = document.xpath("//*[@id='currentPage']/text()")
    if (identity and identity != [notice_id]) or (
        (total > 1 or current) and current != [str(page)]
    ):
        raise ValueError(f"指定と異なる通知またはページが返りました: {url}")

    body = render(container, url).strip()
    if not body:
        raise ValueError(f"本文が空です: {url}")

    attachments = {}
    for link in document.xpath(
        "//div[contains(concat(' ', normalize-space(@class), ' '), ' imgDiv ')]//a[@href]"
    ):
        if is_attachment(link):
            target = http_url(url, link.get("href"))
            if target:
                attachments[target] = node_text(link) or "画像"
    return container, re.sub(r"\n{3,}", "\n\n", body), attachments


def convert(notice_id, source):
    if not isinstance(source, dict) or source.get("notice_id") != notice_id:
        raise ValueError("保存原本の通知IDが一致しません")
    pages = source.get("pages")
    acquired = source.get("acquired")
    if not isinstance(pages, list) or not pages or not all(isinstance(p, str) for p in pages):
        raise ValueError("保存原本にHTML本文がありません")
    if not isinstance(acquired, str):
        raise ValueError("保存原本に取得日がありません")
    datetime.strptime(acquired, "%Y-%m-%d")

    first_page = parse_page(pages[0])
    total = page_count(first_page)
    if len(pages) != total:
        raise ValueError("保存原本のページ数が本文の表示と一致しません")

    body_sections = []
    images = {}
    for page, raw in enumerate(pages, start=1):
        url = page_url(notice_id, page)
        document = first_page if page == 1 else parse_page(raw)
        container, body, attachments = read_page(document, notice_id, page, total)
        if page == 1:
            title = container.xpath(".//p[@class='title-irregular']")
            heading = node_text(title[0]).removeprefix("○") if title else ""
            if not heading:
                title = document.find(".//title")
                heading = node_text(title).removeprefix("・") if title is not None else ""
            if not heading:
                raise ValueError(f"件名を取得できません: {url}")
            metadata = [f"# {markdown_text(heading)}", f"- 通知ID: `{notice_id}`"]
            for css_class, label in (("date", "発出日"), ("number", "通知番号")):
                matches = container.xpath(f".//div[@class='head']//p[@class='{css_class}']")
                if matches and node_text(matches[0]):
                    metadata.append(f"- {label}: {markdown_text(node_text(matches[0]))}")
            metadata.extend((
                f"- 出典: 厚生労働省法令等データベースサービス <{url}>",
                f"- 取得日: {acquired}",
                "- 加工: 原本HTMLをMarkdownへ変換",
            ))
        body_sections.extend((
            f"## 本文（{markdown_link(f'原本 {page}ページ', url)}）", body
        ))
        for image_url, label in attachments.items():
            images.setdefault(image_url, (page, label))

    sections = ["\n".join(metadata), *body_sections]
    if images:
        rows = [
            f"- {markdown_link(label, image_url)}（"
            f"{markdown_link(f'原本 {page}ページ', page_url(notice_id, page))}）"
            for image_url, (page, label) in images.items()
        ]
        sections.extend(("## 添付画像", "\n".join(rows)))
    return "\n\n".join(sections) + "\n"


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
    try:
        temporary.write_bytes(content.encode("utf-8"))
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notice_id", help="通知本文URLの dataId")
    parser.add_argument("--out", type=Path, default=Path("output"), help="出力フォルダ")
    originals = parser.add_mutually_exclusive_group()
    originals.add_argument("--save-source", type=Path, help="取得したHTMLを保存するJSONファイル")
    originals.add_argument("--source", type=Path, help="保存した原本JSONからオフラインで変換")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9]{1,32}", args.notice_id):
        parser.error("通知IDには英数字を指定してください")

    target = args.out / f"{args.notice_id}.md"
    if args.save_source and args.save_source.resolve() == target.resolve():
        parser.error("原本JSONにはMarkdownと異なる出力先を指定してください")
    if args.source and args.source.resolve() == target.resolve():
        parser.error("原本JSONとMarkdownの出力先を分けてください")
    try:
        if args.source:
            source = json.loads(args.source.read_text(encoding="utf-8"))
        else:
            source = download(args.notice_id)
        markdown = convert(args.notice_id, source)
        if args.save_source:
            write_file(args.save_source, json.dumps(source, ensure_ascii=False) + "\n")
        write_file(target, markdown)
    except (OSError, ValueError, etree.LxmlError) as error:
        print(f"変換失敗: {error}", file=sys.stderr)
        return 1
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
