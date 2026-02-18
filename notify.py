"""
FANZA 新着通知スクリプト (notify.py)
=====================================
スプレッドシートに登録された全女優の新作を DMM API で検索し、
history タブに未記録の作品があれば Discord Webhook で通知 & ID を記録する。

使い方:
    python notify.py

環境変数 (または .streamlit/secrets.toml から読み取り):
    - api_id / affiliate_id  : DMM Affiliate API 認証
    - discord_webhook_url    : Discord Webhook URL
"""

import os
import sys
import json
import time
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------------------------------------------------------------------
# 設定読み込み
# ---------------------------------------------------------------------------
SECRETS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml"
)


def load_secrets() -> dict:
    """
    .streamlit/secrets.toml または環境変数から設定を読み込む。
    toml パースは簡易実装 (key = "value" 形式のみ対応)。
    """
    secrets = {}
    if os.path.exists(SECRETS_PATH):
        with open(SECRETS_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    secrets[key] = val

    # 環境変数で上書き可能
    for key in ("api_id", "affiliate_id", "discord_webhook_url"):
        env_val = os.environ.get(key.upper()) or os.environ.get(key)
        if env_val:
            secrets[key] = env_val

    return secrets


secrets = load_secrets()
API_ID = secrets.get("api_id", "")
AFFILIATE_ID = secrets.get("affiliate_id", "")
DISCORD_WEBHOOK_URL = secrets.get("discord_webhook_url", "")

if not API_ID or not AFFILIATE_ID:
    print("[ERROR] api_id / affiliate_id が設定されていません。")
    sys.exit(1)
if not DISCORD_WEBHOOK_URL:
    print("[ERROR] discord_webhook_url が設定されていません。")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Google Sheets 接続
# ---------------------------------------------------------------------------
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

def _load_service_account_from_secrets() -> dict | None:
    """secrets.toml の [gcp_service_account] セクションを読み込む。"""
    if not os.path.exists(SECRETS_PATH):
        return None
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # Python < 3.11 向けフォールバック
    with open(SECRETS_PATH, "rb") as f:
        data = tomllib.load(f)
    sa = data.get("gcp_service_account")
    if sa and isinstance(sa, dict) and "private_key" in sa:
        return dict(sa)
    return None


SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "service_account.json"
)


def get_gspread_client():
    # Secrets TOML 内に gcp_service_account セクションがあれば dict から認証
    sa_info = _load_service_account_from_secrets()
    if sa_info:
        sa_info["private_key"] = sa_info["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_info, SCOPES)
    elif os.path.exists(SERVICE_ACCOUNT_FILE):
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            SERVICE_ACCOUNT_FILE, SCOPES
        )
    else:
        raise FileNotFoundError(
            "service_account.json が見つからず、secrets.toml にも"
            " [gcp_service_account] セクションがありません。"
        )
    return gspread.authorize(creds)


def get_sheet(client, tab_name: str):
    spreadsheet = client.open("fanza_db")
    return spreadsheet.worksheet(tab_name)


# ---------------------------------------------------------------------------
# DMM API
# ---------------------------------------------------------------------------
DMM_ITEM_ENDPOINT = "https://api.dmm.com/affiliate/v3/ItemList"


def search_items_by_actress(actress_id: str, hits: int = 30):
    """指定女優 ID の新着作品を取得。"""
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
    data = resp.json()
    result = data.get("result", {})
    return result.get("items", [])


# ---------------------------------------------------------------------------
# Discord 通知
# ---------------------------------------------------------------------------
def send_discord_notification(actress_name: str, items: list[dict]):
    """Discord Webhook でまとめて通知。"""
    if not items:
        return

    embeds = []
    for item in items[:10]:  # Discord embed は 10 個まで
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

    # 女優一覧を取得
    ws_actresses = get_sheet(client, "actresses")
    actresses = ws_actresses.get_all_records()
    if not actresses:
        print("登録女優がいません。終了します。")
        return

    # 既知の content_id を取得
    ws_history = get_sheet(client, "history")
    history_records = ws_history.get_all_records()
    known_ids = {str(r.get("content_id", "")) for r in history_records}

    total_new = 0

    for act in actresses:
        name = act.get("name", "不明")
        actress_id = str(act.get("actress_id", ""))
        if not actress_id:
            continue

        print(f"  検索中: {name} (ID: {actress_id})")
        try:
            items = search_items_by_actress(actress_id)
        except Exception as e:
            print(f"  [ERROR] API呼び出し失敗: {e}")
            continue

        # 未通知の作品を抽出
        new_items = []
        for item in items:
            cid = item.get("content_id", "")
            if cid and str(cid) not in known_ids:
                new_items.append(item)

        if not new_items:
            print(f"    → 新作なし")
            continue

        print(f"    → 新作 {len(new_items)} 件検出！ Discord へ通知します。")
        total_new += len(new_items)

        # Discord 通知
        send_discord_notification(name, new_items)

        # history に記録
        rows_to_add = []
        for item in new_items:
            cid = str(item.get("content_id", ""))
            title = item.get("title", "")
            date = item.get("date", "")[:10]
            rows_to_add.append([cid, title, date])
            known_ids.add(cid)

        if rows_to_add:
            ws_history.append_rows(rows_to_add)

        # API レートリミット対策
        time.sleep(1)

    print(f"=== 完了: 新作合計 {total_new} 件 ===")


if __name__ == "__main__":
    main()
