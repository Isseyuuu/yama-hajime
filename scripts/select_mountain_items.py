"""楽天APIの商品群から登山用途に合う候補を機械選定する。

商品名で用途を絞るだけで、公式必須装備への適合を保証しない。公開前にClaude Codeが
商品ページで仕様を確認すること。
"""
import argparse
import json
from pathlib import Path
import re
import unicodedata

PROFILES = {
    "boots": {"include": ["登山", "トレッキング", "ハイキング"], "exclude": ["キッズ", "ジュニア", "子供", "サンダル", "インソール", "靴下", "スパッツ", "アイゼン", "スノースパイク", "チェーン", "グリッパー"]},
    "backpacks": {"include": ["バックパック", "リュック", "ザック"], "exclude": ["キッズ", "ジュニア", "子供", "スクール", "ランドセル", "ビジネス", "ポーチ"]},
    "rainwear": {"include": ["レインスーツ", "レインウェア", "雨具", "カッパ"], "require_any": ["上下", "セット", "スーツ"], "exclude": ["キッズ", "ジュニア", "子供", "ポンチョ", "コート", "ジャケットのみ", "パンツのみ"]},
}
PROMO = [r"【[^】]*】", r"＼[^／]*／", r"\([^)]*ポイント[^)]*\)"]
NOISE = ["期間限定", "送料無料", "あす楽", "在庫限り", "セール", "限定価格", "正規品", "公式"]


def normalized(text):
    return unicodedata.normalize("NFKC", text or "").lower()


def clean_name(name):
    value = name or ""
    for _ in range(6):
        before = value
        for pattern in PROMO:
            value = re.sub(pattern, " ", value)
        if value == before:
            break
    for word in NOISE:
        value = value.replace(word, " ")
    return re.sub(r"\s+", " ", value).strip(" 　-–—/／|｜!！★☆、,")


def relevant(name, profile):
    text = normalized(name)
    rule = PROFILES[profile]
    if not any(normalized(word) in text for word in rule["include"]):
        return False
    if any(normalized(word) in text for word in rule["exclude"]):
        return False
    required = rule.get("require_any")
    return not required or any(normalized(word) in text for word in required)


def signature(name):
    text = normalized(name)
    text = re.sub(r"\b(?:メンズ|レディース|ユニセックス|男女兼用|ワイド|幅広)\b", " ", text)
    text = re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠]+", " ", text)
    return " ".join(text.split()[:8])


def main():
    parser = argparse.ArgumentParser(description="登山用品候補の選定")
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--src", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--min-reviews", type=int, default=20)
    parser.add_argument("--min-average", type=float, default=4.0)
    parser.add_argument("--top", type=int, default=8)
    args = parser.parse_args()
    data = json.loads(Path(args.src).read_text(encoding="utf-8"))
    kept = []
    for row in data["items"]:
        name = clean_name(row["itemName"])
        if not relevant(name, args.profile):
            continue
        if row["reviewCount"] < args.min_reviews or row["reviewAverage"] < args.min_average:
            continue
        if not row.get("affiliateUrl") or not row.get("imageUrl"):
            continue
        kept.append(dict(row, itemName=name))
    best = {}
    for row in sorted(kept, key=lambda item: (-item["reviewCount"], -item["reviewAverage"])):
        best.setdefault(signature(row["itemName"]), row)
    selected = list(best.values())[: args.top]
    payload = {"fetchedAt": data.get("fetchedAt"), "source": data.get("source"), "profile": args.profile, "criteria": {"minReviews": args.min_reviews, "minAverage": args.min_average, "note": "商品名による候補選定。必須装備への適合は商品ページで別途確認する。"}, "itemCount": len(selected), "items": selected}
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{args.profile}: {len(selected)}件を{args.out}へ保存")
    for row in selected:
        print(f"  ★{row['reviewAverage']:.2f} ({row['reviewCount']}件) {row['itemName'][:70]}")


if __name__ == "__main__":
    main()
