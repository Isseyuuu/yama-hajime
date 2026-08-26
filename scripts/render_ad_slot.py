"""選定済み商品をコメント封印された楽天広告枠へ描画する。"""
import argparse
import html
import json
from pathlib import Path
import re
import sys

END_MARK = "<!-- /RAKUTEN_AD_SLOT -->"
OLD_END = re.compile(r"/RAKUTEN_AD_SLOT\s*-->")


def esc(value):
    return html.escape(str(value), quote=True)


def card(item):
    name = esc(item["itemName"])
    return f"""      <div class="ad-card">
        <strong>{name}</strong>
        <img src="{esc(item['imageUrl'])}" alt="{name}" width="200" height="200" loading="lazy" decoding="async">
        <small>楽天市場価格の目安：{item['itemPrice']:,}円（{esc(item['taxNote'])}・{esc(item['postageNote'])}・変動あり）</small>
        <small>楽天市場のレビュー：★{item['reviewAverage']:.2f}（{item['reviewCount']:,}件、楽天市場の集計値）</small>
        <a href="{esc(item['affiliateUrl'])}" rel="sponsored nofollow">楽天市場で見る</a>
      </div>"""


def main():
    parser = argparse.ArgumentParser(description="山サイト楽天広告枠の描画")
    parser.add_argument("--src", nargs="+", required=True, help="選定済みJSON")
    parser.add_argument("--pick", nargs="+", type=int, help="各JSONから使う候補順位（1始まり。省略時はすべて1位）")
    parser.add_argument("--article", required=True)
    parser.add_argument("--slot", required=True)
    parser.add_argument("--element-id", required=True)
    parser.add_argument("--heading", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.pick and len(args.pick) != len(args.src):
        sys.exit("--pickは--srcと同じ個数を指定してください。")
    picks = args.pick or [1] * len(args.src)
    if any(rank < 1 for rank in picks):
        sys.exit("--pickは1以上で指定してください。")
    items, dates, seen = [], [], set()
    for source, rank in zip(args.src, picks):
        data = json.loads(Path(source).read_text(encoding="utf-8"))
        dates.append((data.get("fetchedAt") or "")[:10])
        eligible = [row for row in data["items"] if row.get("affiliateUrl") and row.get("imageUrl") and row.get("itemCode") not in seen]
        candidate = eligible[rank - 1] if rank <= len(eligible) else None
        if candidate:
            items.append(candidate)
            seen.add(candidate.get("itemCode"))
        else:
            sys.exit(f"{source}の候補{rank}位を選べません。")
    if not items:
        sys.exit("掲載できるaffiliateUrl付き商品がありません。")
    article = Path(args.article)
    raw = article.read_text(encoding="utf-8")
    start = re.search(r"<!--\s*RAKUTEN_AD_SLOT:\s*" + re.escape(args.slot) + r"(?![\w-])", raw)
    if not start:
        sys.exit(f"RAKUTEN_AD_SLOT: {args.slot} が見つかりません。")
    end = OLD_END.search(raw, start.end())
    if not end:
        sys.exit("終了マーカーが見つかりません。")
    cards = "\n".join(card(item) for item in items)
    fetched = max(date for date in dates if date)
    block = f"""<!-- RAKUTEN_AD_SLOT: {args.slot} 自動生成。更新はscripts/render_ad_slot.pyを再実行 -->
    <div class="cta" id="{esc(args.element_id)}">
      <p class="tag">広告</p>
      <h2>{esc(args.heading)}</h2>
      <p class="source-note">レビュー件数・平均評価は<strong>楽天市場の集計値</strong>であり、当サイトが実測したものではありません。掲載は{esc(fetched)}時点のデータです。価格・在庫・送料条件は変動するため、商品ページで最新条件を確認してください。商品名による候補選定であり、富士登山の装備基準への適合を保証するものではありません。</p>
      <div class="ad-options">
{cards}
      </div>
    </div>
    {END_MARK}"""
    updated = raw[: start.start()] + block + raw[end.end():]
    print(f"{args.slot}: {len(items)}件")
    for item in items:
        print(f"  {item['itemName'][:70]}")
    if args.dry_run:
        print("--dry-run: 書き込みなし")
        return
    with article.open("w", encoding="utf-8", newline="") as output:
        output.write(updated)
    print(f"{article}を更新")


if __name__ == "__main__":
    main()
