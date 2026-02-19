"""
daily_notifier.py − GitHub Actions 用 FANZA 新着通知
=====================================================
登録女優の新作を DMM API で検索し、未通知の作品を Discord へ通知する。
フィルタリングは filters.py の共通ロジックを使用。

認証優先順位:
  1. 環境変数 GCP_SERVICE_ACCOUNT_JSON (JSON文字列)
  2. ローカルの service_account.json ファイル
"""

import os
import sys
import json
import time
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from filters import filter_items

# ---------------------------------------------------------------------------
# 設定読み込み
# ---------------------------------------------------------------------------
API_ID = os.environ.get("DMM_API_ID", "")
AFFILIATE_ID = os.environ.get("DMM_AFFILIATE_ID", "")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

if not API_ID or not AFFILIATE_ID:
    print("[ERROR] DMM_API_ID / DMM_AFFILIATE_ID が設定されていません。")
    sys.exit(1)
if not DISCORD_WEBHOOK_URL:
    print("[ERROR] DISCORD_WEBHOOK_URL が設定されていません。")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Google Sheets 接続
# ---------------------------------------------------------------------------
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "service_account.json"
)


def get_gspread_client():
    """GCP サービスアカウント認証。環境変数 → ファイルの順にフォールバック。"""
    sa_json = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "")
    if sa_json:
        sa_info = json.loads(sa_json)
        # private_key の改行を正規化
        p_key = sa_info["private_key"].replace("\\n", "\n")
        sa_info["private_key"] = "\n".join(
            [line.strip() for line in p_key.split("\n") if line.strip()]
        )
        creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_info, SCOPES)
    elif os.path.exists(SERVICE_ACCOUNT_FILE):
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            SERVICE_ACCOUNT_FILE, SCOPES
        )
    else:
        raise FileNotFoundError(
            "GCP_SERVICE_ACCOUNT_JSON 環境変数が未設定で、"
            "service_account.json も見つかりません。"
        )
    return gspread.authorize(creds)


def get_sheet(client, tab_name: str):
    return client.open("fanza_db").worksheet(tab_name)


def ensure_sheet(client, tab_name: str, headers: list[str]):
    """シートが無ければ作成、ヘッダーがなければ追加。"""
    try:
        ws = get_sheet(client, tab_name)
    except gspread.exceptions.WorksheetNotFound:
        spreadsheet = client.open("fanza_db")
        ws = spreadsheet.add_worksheet(title=tab_name, rows=100, cols=len(headers))
        ws.append_row(headers)
    return ws


# ---------------------------------------------------------------------------
# DMM API
# ---------------------------------------------------------------------------
DMM_ITEM_ENDPOINT = "https://api.dmm.com/affiliate/v3/ItemList"


def search_items_by_actress(actress_id: str, hits: int = 30) -> list[dict]:
    params = {
        "api_id": API_ID,
        "affiliate_id": AFFILIATE_ID,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "article": "actress",
        "article_id": actress_id,
        "hits": hits,
        "sort": "date",
        "output": "json",
    }
    resp = requests.get(DMM_ITEM_ENDPOINT, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("result", {}).get("items", [])


# ---------------------------------------------------------------------------
# Discord 通知
# ---------------------------------------------------------------------------
def send_discord_notification(actress_name: str, items: list[dict]):
    if not items:
        return

    embeds = []
    for item in items[:10]:
        title = item.get("title", "タイトル不明")
        url = item.get("affiliateURL") or item.get("URL", "")
        date = item.get("date", "")[:10]
        img_url = (
            item.get("imageURL", {}).get("large", "")
            or item.get("imageURL", {}).get("small", "")
        )
        embed = {
            "title": title,
            "url": url,
            "color": 0xFF6699,
            "fields": [{"name": "発売日", "value": date, "inline": True}],
        }
        if img_url:
            embed["thumbnail"] = {"url": img_url}
        embeds.append(embed)

    payload = {
        "content": f"🎬 **{actress_name}** の新作が {len(items)} 件見つかりました！",
        "embeds": embeds,
    }

    resp = requests.post(
        DISCORD_WEBHOOK_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    if resp.status_code not in (200, 204):
        print(f"[WARN] Discord通知失敗 (status={resp.status_code}): {resp.text}")


# ---------------------------------------------------------------------------
# メイン処理
# ---------------------------------------------------------------------------
def main():
    print("=== FANZA 新着通知スクリプト開始 ===")

    client = get_gspread_client()

    # 女優一覧
    ws_actresses = get_sheet(client, "actresses")
    actresses = ws_actresses.get_all_records()
    if not actresses:
        print("登録女優がいません。終了します。")
        return

    # 通知履歴 (sent_works)
    ws_sent = ensure_sheet(client, "sent_works", ["content_id", "title", "date", "actress_name"])
    sent_records = ws_sent.get_all_records()
    known_ids = {str(r.get("content_id", "")) for r in sent_records}

    total_new = 0

    for act in actresses:
        name = act.get("name", "不明")
        actress_id = str(act.get("actress_id", ""))
        if not actress_id:
            continue

        print(f"  検索中: {name} (ID: {actress_id})")
        try:
            raw_items = search_items_by_actress(actress_id)
            # 共通フィルタ (max_items を大きめに設定して通知漏れを防ぐ)
            items = filter_items(raw_items, max_items=30)
        except Exception as e:
            print(f"  [ERROR] API呼び出し失敗: {e}")
            continue

        # 未通知の作品を抽出
        new_items = [
            item for item in items
            if item.get("content_id") and str(item["content_id"]) not in known_ids
        ]

        if not new_items:
            print(f"    → 新作なし")
            continue

        print(f"    → 新作 {len(new_items)} 件検出！ Discord へ通知します。")
        total_new += len(new_items)

        # Discord 通知
        send_discord_notification(name, new_items)

        # sent_works に記録
        rows_to_add = []
        for item in new_items:
            cid = str(item.get("content_id", ""))
            title = item.get("title", "")
            date = item.get("date", "")[:10]
            rows_to_add.append([cid, title, date, name])
            known_ids.add(cid)

        if rows_to_add:
            ws_sent.append_rows(rows_to_add)

        # API レートリミット対策
        time.sleep(1)

    print(f"=== 完了: 新作合計 {total_new} 件 ===")


if __name__ == "__main__":
    main()
