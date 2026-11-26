"""Download MHLW document attachment images referenced by saved source HTML."""

import argparse
import json
from pathlib import Path
import re
import sys
from time import sleep
from urllib.request import Request, urlopen

from lxml import etree

from notice_to_md import image_id, image_links, page_url, parse_page, read_page, source_pages, write_bytes


IMAGE_ENDPOINT = "https://www.mhlw.go.jp/web/t_img_res"
IMAGE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/tiff": ".tif",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
}


def find_images(source):
    notice_id = source.get("notice_id") if isinstance(source, dict) else None
    if not isinstance(notice_id, str) or not re.fullmatch(r"[A-Za-z0-9]{1,32}", notice_id):
        raise ValueError("保存原本の通知IDが不正です")

    pages, first_page, _, data_type = source_pages(notice_id, source)
    identifiers = {}
    for page, raw in enumerate(pages, start=1):
        url = page_url(notice_id, page, data_type)
        document = first_page if page == 1 else parse_page(raw)
        container, _, attachments = read_page(document, notice_id, page, len(pages), data_type)
        body_images = image_links(container.xpath(".//a[@href]"), url)
        for target in (*body_images, *attachments):
            identifier = image_id(target)
            if identifier is not None:
                identifiers[identifier] = None
    return identifiers.keys()


def download_image(identifier, directory):
    url = f"{IMAGE_ENDPOINT}?img={identifier}"
    request = Request(url, headers={"User-Agent": "MHLW_houreiDB/0.1 (notice converter)"})
    with urlopen(request, timeout=30) as response:
        extension = IMAGE_EXTENSIONS.get(response.headers.get_content_type())
        if extension is None:
            raise ValueError(f"対応する画像形式を取得できませんでした: {url}")
        content = response.read()
    if not content:
        raise ValueError(f"空の画像が返りました: {url}")

    target = directory / f"{identifier}{extension}"
    write_bytes(target, content)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="--save-source で保存した原本JSON")
    parser.add_argument("--out", type=Path, default=Path("output/ocr-input"), help="画像の保存先")
    args = parser.parse_args()

    try:
        source = json.loads(args.source.read_text(encoding="utf-8"))
        identifiers = find_images(source)
    except (OSError, ValueError, etree.LxmlError) as error:
        print(f"原本の読み込み失敗: {error}", file=sys.stderr)
        return 1
    if not identifiers:
        print("対象の添付画像はありません")
        return 0

    failed = False
    for index, identifier in enumerate(identifiers):
        if index:
            sleep(1)
        try:
            print(download_image(identifier, args.out))
        except (OSError, ValueError) as error:
            print(f"画像 {identifier} の取得失敗: {error}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
