"""公開HTML内のアフィリエイトリンクが到達可能か確認する。"""
import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlparse


class SponsoredLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        values = dict(attrs)
        rel = set((values.get("rel") or "").split())
        href = values.get("href") or ""
        if "sponsored" in rel and href.startswith(("http://", "https://")):
            self.links.append(href)


def main():
    parser = argparse.ArgumentParser(description="公開アフィリエイトリンクの到達確認")
    parser.add_argument("paths", nargs="*", default=["articles"], help="HTMLファイルまたはディレクトリ")
    parser.add_argument("--timeout", type=int, default=25)
    args = parser.parse_args()
    urls = []
    for raw_path in args.paths:
        path = Path(raw_path)
        files = sorted(path.glob("*.html")) if path.is_dir() else [path]
        for html_file in files:
            public = re.sub(r"<!--.*?-->", "", html_file.read_text(encoding="utf-8"), flags=re.S)
            collector = SponsoredLinks()
            collector.feed(public)
            urls.extend(collector.links)
    urls = list(dict.fromkeys(urls))
    if not urls:
        sys.exit("公開アフィリエイトリンクがありません。")
    failures = []
    for index, url in enumerate(urls, 1):
        command = ["curl.exe", "--location", "--silent", "--show-error", "--output", "NUL", "--write-out", "%{http_code}\t%{url_effective}", "--max-time", str(args.timeout)]
        if sys.platform.startswith("win"):
            command.insert(1, "--ssl-no-revoke")
        result = subprocess.run(command + [url], capture_output=True, text=True, encoding="utf-8", errors="replace")
        parts = result.stdout.strip().split("\t", 1)
        status = parts[0] if parts else "000"
        effective = parts[1] if len(parts) > 1 else ""
        domain = urlparse(effective or url).netloc
        ok = result.returncode == 0 and status.isdigit() and 200 <= int(status) < 400
        print(f"{index:02d} {'OK' if ok else 'NG'} HTTP {status} {domain}")
        if not ok:
            failures.append((status, domain, result.stderr.strip()))
    if failures:
        for status, domain, error in failures:
            print(f"ERROR HTTP {status} {domain} {error}")
        sys.exit(1)
    print(f"OK: {len(urls)}本の公開アフィリエイトリンクが到達可能")


if __name__ == "__main__":
    main()
