"""楽天市場APIから山道具の商品候補を取得する。

WindowsのPythonにSSLモジュールがない環境でも動くよう、HTTPS通信はcurlを使う。
認証情報は指定した.envから読み、標準出力や保存JSONには含めない。
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
JST = timezone(timedelta(hours=9))
MAX_HITS = 30


def load_env(path):
    values = {}
    env_path = Path(path)
    if not env_path.exists():
        return values
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def credentials(env_file):
    values = load_env(env_file)
    app_id = os.environ.get("RAKUTEN_APP_ID") or values.get("RAKUTEN_APP_ID")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY") or values.get("RAKUTEN_ACCESS_KEY")
    affiliate_id = os.environ.get("RAKUTEN_AFFILIATE_ID") or values.get("RAKUTEN_AFFILIATE_ID")
    if not app_id or not access_key:
        sys.exit("RAKUTEN_APP_ID と RAKUTEN_ACCESS_KEY が未設定です。")
    return app_id, access_key, affiliate_id


def curl_json(params):
    command = ["curl.exe" if os.name == "nt" else "curl", "-sS", "--get", ENDPOINT]
    if os.name == "nt":
        command.append("--ssl-no-revoke")
    for key, value in params.items():
        if value is not None:
            command.extend(["--data-urlencode", f"{key}={value}"])
    command.extend(["-H", "User-Agent: yama-hajime/1.0"])
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        sys.exit(f"curl failed ({result.returncode}): {result.stderr.strip()}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        sys.exit(f"楽天APIのJSONを解析できません: {exc}")
    if data.get("error"):
        sys.exit(f"楽天API error: {data.get('error_description') or data['error']}")
    return data


def strip_tags(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def normalize(item):
    return {
        "itemCode": item.get("itemCode"),
        "itemName": strip_tags(item.get("itemName")),
        "shopName": item.get("shopName"),
        "itemPrice": item.get("itemPrice"),
        "taxFlag": item.get("taxFlag"),
        "taxNote": "税抜" if item.get("taxFlag") == 1 else "税込",
        "postageFlag": item.get("postageFlag"),
        "postageNote": "送料別" if item.get("postageFlag") == 1 else "送料込",
        "reviewCount": item.get("reviewCount", 0),
        "reviewAverage": float(item.get("reviewAverage") or 0),
        "itemUrl": item.get("itemUrl"),
        "affiliateUrl": item.get("affiliateUrl") or "",
        "imageUrl": (item.get("mediumImageUrls") or [{}])[0].get("imageUrl", ""),
    }


def main():
    parser = argparse.ArgumentParser(description="楽天市場APIから山道具候補を取得")
    parser.add_argument("--genre", type=int, required=True)
    parser.add_argument("--keyword")
    parser.add_argument("--pages", type=int, default=4)
    parser.add_argument("--min-reviews", type=int, default=20)
    parser.add_argument("--sort", default="-reviewCount")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if not 1 <= args.pages <= 100:
        parser.error("--pages は1〜100で指定してください")

    app_id, access_key, affiliate_id = credentials(args.env_file)
    base = {
        "applicationId": app_id,
        "accessKey": access_key,
        "affiliateId": affiliate_id,
        "genreId": args.genre,
        "keyword": args.keyword,
        "hits": MAX_HITS,
        "sort": args.sort,
        "format": "json",
    }
    unique = {}
    for page in range(1, args.pages + 1):
        data = curl_json(dict(base, page=page))
        batch = data.get("Items") or []
        if not batch:
            break
        for entry in batch:
            row = normalize(entry.get("Item", entry))
            if row["itemCode"]:
                unique[row["itemCode"]] = row
        print(f"page {page}: {len(batch)}件（ユニーク{len(unique)}件）")
        if page < args.pages:
            time.sleep(1)

    rows = [row for row in unique.values() if row["reviewCount"] >= args.min_reviews]
    rows.sort(key=lambda row: (-row["reviewCount"], -row["reviewAverage"]))
    payload = {
        "fetchedAt": datetime.now(JST).isoformat(timespec="seconds"),
        "source": "楽天市場 商品検索API（レビュー件数・平均評価は楽天市場の集計値）",
        "query": {"genreId": args.genre, "keyword": args.keyword, "pages": args.pages, "minReviews": args.min_reviews, "sort": args.sort},
        "itemCount": len(rows),
        "items": rows,
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(rows)}件を{output}へ保存")


if __name__ == "__main__":
    main()
