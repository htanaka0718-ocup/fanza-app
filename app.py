"""
AV Monitor - 新着チェック Web アプリ
=====================================
登録女優の新作（通販/予約情報）をDMM APIで検索し、
グループ別に横スクロールカードで一覧表示する。
サイドバー（デフォルト非表示）で女優の一括検索・追加、
編集モードでグループ管理が可能。
"""

import re
import streamlit as st
import requests
import gspread
import pandas as pd
import urllib.parse
from streamlit_sortables import sort_items
from oauth2client.service_account import ServiceAccountCredentials

# ---------------------------------------------------------------------------
# ページ設定 & カスタムCSS (ブラック × ピンク テーマ)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AV Monitor",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    /* ===== グローバル ===== */
    :root {
        --bg:       #0a0a0a;
        --bg-card:  #141414;
        --bg-hover: #1e1e1e;
        --pink:     #ff4d8d;
        --pink-dim: #cc3d71;
        --txt:      #f0f0f0;
        --txt-sub:  #bbb;
    }
    html, body, [data-testid="stAppViewContainer"],
    [data-testid="stSidebar"], [data-testid="stHeader"],
    .main .block-container {
        background-color: var(--bg) !important;
        color: var(--txt) !important;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d0d0d 0%, #111 100%) !important;
        border-right: 1px solid #222 !important;
    }
    /* サイドバー内の全テキスト */
    [data-testid="stSidebar"] * {
        color: var(--txt) !important;
    }
    [data-testid="stHeader"] { background: transparent !important; }
    .block-container { max-width: 100%; padding: 1rem 2rem; }

    /* ===== ボタン全般 ===== */
    .stButton > button,
    .stFormSubmitButton > button,
    button[kind="secondary"],
    button[data-testid="stBaseButton-secondary"] {
        background: var(--bg-card) !important;
        color: var(--txt) !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease;
    }
    .stButton > button:hover,
    .stFormSubmitButton > button:hover {
        border-color: var(--pink) !important;
        color: var(--pink) !important;
        box-shadow: 0 0 8px rgba(255,77,141,0.25);
    }
    /* プライマリボタン */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"],
    button[data-testid="stBaseButton-primary"],
    [data-testid="stFormSubmitButton"] > button {
        background: var(--pink) !important;
        border: none !important;
        color: #fff !important;
    }
    .stButton > button[kind="primary"]:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        background: var(--pink-dim) !important;
        box-shadow: 0 0 12px rgba(255,77,141,0.4);
    }

    /* ===== ボタンクリック範囲拡大 ===== */
    .stButton > button,
    .stFormSubmitButton > button {
        min-height: 38px !important;
        padding: 6px 16px !important;
        cursor: pointer !important;
    }

    /* ===== Expander (白背景を完全排除) ===== */
    [data-testid="stExpander"] {
        background: var(--bg-card) !important;
        border: 1px solid #222 !important;
        border-radius: 10px !important;
        margin-bottom: 8px;
    }
    details {
        background: var(--bg-card) !important;
        color: var(--txt) !important;
    }
    details > summary {
        background: var(--bg-card) !important;
        color: var(--txt) !important;
        font-weight: 600;
    }
    details > summary *,
    details > summary span,
    details > summary p {
        color: var(--txt) !important;
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p {
        color: var(--txt) !important;
        font-weight: 600;
    }
    [data-testid="stExpander"] > div,
    [data-testid="stExpander"] > div > div {
        background: var(--bg-card) !important;
        color: var(--txt) !important;
    }
    [data-testid="stExpander"] summary:hover,
    [data-testid="stExpander"] summary:hover span,
    details > summary:hover,
    details > summary:hover * {
        color: var(--pink) !important;
    }

    /* ===== textarea ヒント (Ctrl+Enter) を隠す ===== */
    [data-testid="stTextArea"] .stTextArea-instructions,
    [data-testid="stTextArea"] div[data-testid="InputInstructions"],
    div[data-testid="InputInstructions"] {
        display: none !important;
    }

    /* ===== Popover ===== */
    [data-testid="stPopover"] > div,
    [data-testid="stPopoverBody"],
    [data-testid="stPopoverBody"] > div {
        background: var(--bg-card) !important;
        border: 1px solid #333 !important;
        color: var(--txt) !important;
    }
    [data-testid="stPopoverBody"] p,
    [data-testid="stPopoverBody"] span,
    [data-testid="stPopoverBody"] label,
    [data-testid="stPopoverBody"] .stMarkdown {
        color: var(--txt) !important;
    }

    /* ===== Form 内部 ===== */
    [data-testid="stForm"] {
        background: var(--bg-card) !important;
        border: 1px solid #222 !important;
        border-radius: 10px !important;
        padding: 12px !important;
    }
    [data-testid="stForm"] label,
    [data-testid="stForm"] span,
    [data-testid="stForm"] p {
        color: var(--txt) !important;
    }

    /* ===== Dialog / Toast ===== */
    [data-testid="stDialog"] > div,
    [data-testid="stToast"],
    div[role="dialog"],
    div[data-modal-container="true"] {
        background: var(--bg-card) !important;
        color: var(--txt) !important;
    }

    /* ===== Checkbox / Radio ===== */
    .stCheckbox label span,
    .stRadio label span {
        color: var(--txt) !important;
    }

    /* ===== Baseweb (内部 UI ライブラリ) ===== */
    div[data-baseweb] { color: var(--txt) !important; }
    div[data-baseweb="popover"] { background: var(--bg-card) !important; }
    div[data-baseweb="select"] > div {
        background: #1a1a1a !important;
        border-color: #333 !important;
        color: var(--txt) !important;
    }
    /* selectbox / listbox ドロップダウン (予測欄) */
    ul[data-baseweb="menu"],
    div[data-baseweb="popover"] > div,
    [data-baseweb="list"] {
        background: var(--bg-card) !important;
    }
    ul[data-baseweb="menu"] li,
    [data-baseweb="list"] li,
    [role="listbox"] li,
    [role="option"] {
        background: var(--bg-card) !important;
        color: var(--txt) !important;
    }

    /* ===== 入力 ===== */
    input, textarea, [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        background: #1a1a1a !important;
        color: var(--txt) !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
    }
    input:focus, textarea:focus { border-color: var(--pink) !important; }

    /* selectbox */
    [data-testid="stSelectbox"] > div > div {
        background: #1a1a1a !important;
        border: 1px solid #333 !important;
    }

    /* ===== テキスト可読性 (包括的) ===== */
    p, li, label, span, .stMarkdown, .stCaption,
    [data-testid="stText"], [data-testid="stCaptionContainer"],
    [data-testid="stMarkdownContainer"] {
        color: var(--txt) !important;
    }
    .stCaption, [data-testid="stCaptionContainer"] p {
        color: var(--txt-sub) !important;
    }
    h1, h2, h3, h4, h5, h6 { color: var(--txt) !important; }
    code { color: var(--pink) !important; background: #1a1a1a !important; }
    .stAlert p { color: var(--txt) !important; }

    /* --- 女優ヘッダー --- */
    .actress-hdr {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 6px 0 8px;
    }
    .actress-hdr img {
        width: 44px; height: 44px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid var(--pink);
        flex-shrink: 0;
    }
    .actress-hdr .name {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--txt);
        white-space: nowrap;
    }
    .actress-hdr a.missav {
        font-size: 0.75rem;
        color: var(--pink);
        text-decoration: none;
        white-space: nowrap;
    }
    .actress-hdr a.missav:hover { text-decoration: underline; }

    /* --- 横スクロール --- */
    .hscroll {
        display: flex;
        overflow-x: auto;
        gap: 12px;
        padding: 4px 0 16px;
        -webkit-overflow-scrolling: touch;
        scroll-snap-type: x mandatory;
    }
    .hscroll::-webkit-scrollbar { height: 4px; }
    .hscroll::-webkit-scrollbar-track { background: transparent; }
    .hscroll::-webkit-scrollbar-thumb {
        background: var(--pink-dim); border-radius: 4px;
    }
    .hscroll::-webkit-scrollbar-thumb:hover { background: var(--pink); }

    /* --- 作品カード --- */
    .icard {
        flex: 0 0 150px;
        scroll-snap-align: start;
        text-decoration: none;
        color: inherit;
        transition: transform 0.15s ease;
    }
    .icard:hover { transform: scale(1.04); }
    .icard img {
        width: 150px;
        height: 210px;
        object-fit: cover;
        border-radius: 8px;
        display: block;
        border: 1px solid #222;
    }
    .icard .ttl {
        font-size: 0.72rem;
        font-weight: 600;
        color: #f0f0f0;
        margin-top: 4px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        white-space: normal;
        line-height: 1.3;
    }
    .icard .dt {
        font-size: 0.65rem;
        color: var(--pink);
        margin-top: 2px;
    }

    /* 区切り線 */
    hr { border-color: #222 !important; }

    /* サイドバー検索結果カード */
    .sr-card {
        background: var(--bg-hover);
        border: 1px solid #333;
        border-radius: 8px;
        padding: 8px 10px;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .sr-card img {
        width: 40px; height: 40px;
        border-radius: 50%;
        object-fit: cover;
        border: 1px solid var(--pink);
    }
    .sr-card .sr-name {
        font-weight: 600;
        color: var(--txt);
        font-size: 0.85rem;
    }
    .sr-card .sr-id {
        font-size: 0.7rem;
        color: var(--pink);
    }

    @media (max-width: 768px) {
        .block-container { padding: 0.5rem; }
        .icard { flex: 0 0 130px; }
        .icard img { width: 130px; height: 182px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 定数 & 除外フィルタ
# ---------------------------------------------------------------------------
EXCLUDE_WORDS = [
    "ベスト", "総集編", "傑作選", "プレミアム",
    "BEST", "100選", "4時間", "8時間", "【数量限定】",
]
EXCLUDE_TITLE_PREFIXES = ["【FANZA限定】", "【特選アウトレット】", "【プレコレ】", "【特典版】"]
EXCLUDE_TITLE_SUFFIXES = ["（BOD）", "（ブルーレイディスク）"]
EXCLUDE_GENRES = ["4時間以上作品", "VR専用"]
_DUPE_PATTERN = re.compile(r"と同じ内容です。")
MAX_PERFORMERS = 4
MAX_ITEMS_PER_ACTRESS = 5

# ---------------------------------------------------------------------------
# セッションステート初期化
# ---------------------------------------------------------------------------
for key, default in {
    "search_results": {},       # name -> [actress dicts]
    "search_error": "",
    "add_success": "",
    "edit_mode": False,
    "items_cache": {},
    "pending_names": "",        # 検索待ち名前テキスト
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------------------------------------------------------------------
# Google Sheets 接続
# ---------------------------------------------------------------------------
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
SERVICE_ACCOUNT_FILE = "service_account.json"


@st.cache_resource(ttl=300)
def _get_gspread_client():
    if "gcp_service_account" in st.secrets:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            dict(st.secrets["gcp_service_account"]), SCOPES
        )
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            SERVICE_ACCOUNT_FILE, SCOPES
        )
    return gspread.authorize(creds)


def get_sheet(tab_name: str):
    client = _get_gspread_client()
    return client.open("fanza_db").worksheet(tab_name)


# ---------------------------------------------------------------------------
# DMM API ヘルパー
# ---------------------------------------------------------------------------
API_ID = st.secrets["api_id"]
AFFILIATE_ID = st.secrets["affiliate_id"]
DMM_ITEM_ENDPOINT = "https://api.dmm.com/affiliate/v3/ItemList"
DMM_ACTRESS_ENDPOINT = "https://api.dmm.com/affiliate/v3/ActressSearch"


def search_actress_api(keyword: str, hits: int = 10):
    params = {
        "api_id": API_ID,
        "affiliate_id": AFFILIATE_ID,
        "keyword": keyword,
        "hits": hits,
        "output": "json",
    }
    resp = requests.get(DMM_ACTRESS_ENDPOINT, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("result", {}).get("actress", [])


def search_items_by_actress(actress_id: str, hits: int = 30):
    """API検索結果をセッションキャッシュし、rerun時の再取得を防ぐ。"""
    cache = st.session_state.items_cache
    if actress_id in cache:
        return cache[actress_id]

    params = {
        "api_id": API_ID,
        "affiliate_id": AFFILIATE_ID,
        "site": "FANZA",
        "service": "mono",
        "floor": "dvd",
        "article": "actress",
        "article_id": actress_id,
        "hits": hits,
        "sort": "date",
        "output": "json",
    }
    resp = requests.get(DMM_ITEM_ENDPOINT, params=params, timeout=15)
    resp.raise_for_status()
    items = resp.json().get("result", {}).get("items", [])
    cache[actress_id] = items
    return items


def make_item_url(content_id: str) -> str:
    return f"https://www.dmm.co.jp/mono/dvd/-/detail/=/cid={content_id}/"


def filter_items(items: list[dict]) -> list[dict]:
    filtered = []
    for item in items:
        title = item.get("title", "")
        if any(w in title for w in EXCLUDE_WORDS):
            continue
        if any(title.startswith(p) for p in EXCLUDE_TITLE_PREFIXES):
            continue
        if any(title.rstrip().endswith(s) for s in EXCLUDE_TITLE_SUFFIXES):
            continue
        genres = item.get("iteminfo", {}).get("genre", [])
        genre_names = [g.get("name", "") for g in genres]
        if any(eg in genre_names for eg in EXCLUDE_GENRES):
            continue
        performers = item.get("iteminfo", {}).get("actress", [])
        if len(performers) > MAX_PERFORMERS:
            continue
        item_desc = item.get("iteminfo", {}).get("comment", "")
        if isinstance(item_desc, str) and _DUPE_PATTERN.search(item_desc):
            continue
        review = item.get("review", "") or ""
        if isinstance(review, str) and _DUPE_PATTERN.search(review):
            continue
        filtered.append(item)
        if len(filtered) >= MAX_ITEMS_PER_ACTRESS:
            break
    return filtered


# ---------------------------------------------------------------------------
# スプシ操作ヘルパー
# ---------------------------------------------------------------------------
def get_all_actresses(force_refresh: bool = False) -> pd.DataFrame:
    if not force_refresh and "df_actresses_cache" in st.session_state:
        return st.session_state.df_actresses_cache
    ws = get_sheet("actresses")
    records = ws.get_all_records()
    if not records:
        df = pd.DataFrame(columns=["name", "actress_id", "image_url", "group"])
    else:
        df = pd.DataFrame(records)
        if "group" not in df.columns:
            df["group"] = ""
        df["group"] = df["group"].fillna("").astype(str)
    st.session_state.df_actresses_cache = df
    return df


def _invalidate_actress_cache():
    st.session_state.pop("df_actresses_cache", None)
    _get_gspread_client.clear()


def add_actresses_batch(actress_list: list[tuple[str, str, str]]):
    ws = get_sheet("actresses")
    rows = [[name, str(aid), img, ""] for name, aid, img in actress_list]
    ws.append_rows(rows)
    _invalidate_actress_cache()


def delete_actress(actress_id: str):
    ws = get_sheet("actresses")
    records = ws.get_all_records()
    for i, r in enumerate(records, start=2):
        if str(r.get("actress_id")) == str(actress_id):
            ws.delete_rows(i)
            break
    _invalidate_actress_cache()


def _rebuild_sheet(df: pd.DataFrame):
    ws = get_sheet("actresses")
    ws.clear()
    ws.append_row(["name", "actress_id", "image_url", "group"])
    if not df.empty:
        rows = df[["name", "actress_id", "image_url", "group"]].values.tolist()
        ws.append_rows(rows)
    _invalidate_actress_cache()


def save_actress_order(ordered_groups: list[dict]):
    ws = get_sheet("actresses")
    records = ws.get_all_records()
    id_map = {}
    for r in records:
        id_map[str(r.get("actress_id", ""))] = r

    new_rows = []
    for container in ordered_groups:
        group_name = container["header"]
        actual_group = group_name if group_name != "未分類" else ""
        for label in container["items"]:
            aid = label.rsplit("[", 1)[-1].rstrip("]").strip()
            if aid in id_map:
                r = id_map[aid]
                new_rows.append([
                    r.get("name", ""),
                    str(r.get("actress_id", "")),
                    r.get("image_url", ""),
                    actual_group,
                ])

    ws.clear()
    ws.append_row(["name", "actress_id", "image_url", "group"])
    if new_rows:
        ws.append_rows(new_rows)
    _invalidate_actress_cache()


def swap_actress_order(df: pd.DataFrame, idx_a: int, idx_b: int):
    rows = df.values.tolist()
    rows[idx_a], rows[idx_b] = rows[idx_b], rows[idx_a]
    new_df = pd.DataFrame(rows, columns=df.columns)
    _rebuild_sheet(new_df)


# ---------------------------------------------------------------------------
# コールバック
# ---------------------------------------------------------------------------
def _cb_batch_add():
    """検索結果から全女優を一括登録する。"""
    all_results = st.session_state.search_results
    collected = []
    for name, results in all_results.items():
        if len(results) == 1:
            act = results[0]
            aid = str(act.get("id", ""))
            img = (
                act.get("imageURL", {}).get("small", "")
                or act.get("imageURL", {}).get("large", "")
            )
            collected.append((act.get("name", name), aid, img))
        else:
            for act in results:
                aid = str(act.get("id", ""))
                if st.session_state.get(f"chk_{aid}", False):
                    img = (
                        act.get("imageURL", {}).get("small", "")
                        or act.get("imageURL", {}).get("large", "")
                    )
                    collected.append((act.get("name", name), aid, img))
    if collected:
        try:
            add_actresses_batch(collected)
            names = ", ".join(c[0] for c in collected)
            st.session_state.add_success = names
            st.session_state.search_results = {}
        except Exception as e:
            st.session_state.search_error = f"追加失敗: {e}"


def _cb_swap(df, idx_a, idx_b):
    swap_actress_order(df, idx_a, idx_b)
    st.session_state.items_cache = {}


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------
def parse_names(text: str) -> list[str]:
    """カンマ・改行・全角スペースなどで区切って名前リストを返す。"""
    names = re.split(r"[,、\n\r\t　]+", text.strip())
    return [n.strip() for n in names if n.strip()]


def render_actress_header(name: str, image_url: str):
    missav = "https://missav.ai/ja/search/" + urllib.parse.quote(name)
    img = f'<img src="{image_url}" alt="">' if image_url else ""
    st.markdown(
        f'<div class="actress-hdr">'
        f"  {img}"
        f'  <span class="name">{name}</span>'
        f'  <a class="missav" href="{missav}" target="_blank">[MissAV]</a>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_hscroll(items: list[dict]):
    if not items:
        st.caption("新作なし")
        return

    cards = []
    for item in items:
        title = item.get("title", "タイトル不明")
        date = item.get("date", "")[:10]
        cid = item.get("content_id", "")
        url = make_item_url(cid) if cid else "#"
        img = (
            item.get("imageURL", {}).get("large", "")
            or item.get("imageURL", {}).get("small", "")
        )
        img_tag = f'<img src="{img}" loading="lazy">' if img else ""
        cards.append(
            f'<a class="icard" href="{url}" target="_blank">'
            f"  {img_tag}"
            f'  <div class="ttl">{title}</div>'
            f'  <div class="dt">📅 {date}</div>'
            f"</a>"
        )

    st.markdown(
        '<div class="hscroll">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# サイドバー: 女優一括検索 & 追加
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔍 女優追加")
    st.caption("名前をカンマ区切りで入力し「検索」を押してください。")

    if st.session_state.add_success:
        st.success(f"{st.session_state.add_success} を追加しました！")
        st.session_state.add_success = ""

    if st.session_state.search_error:
        st.error(st.session_state.search_error)
        st.session_state.search_error = ""

    with st.form("multi_search_form", clear_on_submit=False):
        query = st.text_area(
            "女優名（カンマ区切り）",
            placeholder="深田えいみ, 三上悠亜, 橋本ありな",
            height=80,
        )
        submitted = st.form_submit_button("検索", use_container_width=True)

    if submitted and query:
        names = parse_names(query)
        old_results = dict(st.session_state.search_results)
        errors = []
        for name in names:
            if name in old_results:
                continue  # 既に検索済み
            try:
                found = search_actress_api(name, hits=5)
                if found:
                    old_results[name] = found
                else:
                    errors.append(f"「{name}」: 見つかりません")
            except Exception as e:
                errors.append(f"「{name}」: {e}")
        st.session_state.search_results = old_results
        if errors:
            st.session_state.search_error = " / ".join(errors)
        st.rerun()

    # --- 蓄積された結果表示 ---
    if st.session_state.search_results:
        all_results = st.session_state.search_results
        st.markdown(f"**検索結果: {len(all_results)}名**")

        st.button(
            "✅ まとめて登録",
            use_container_width=True, type="primary",
            on_click=_cb_batch_add, key="batch_add_btn",
        )

        if st.button("🗑️ 検索結果をクリア", use_container_width=True):
            st.session_state.search_results = {}
            st.rerun()

        for search_name, results in all_results.items():
            st.markdown(f"**{search_name}**")
            if len(results) == 1:
                act = results[0]
                aname = act.get("name", "不明")
                aid = str(act.get("id", ""))
                img = (
                    act.get("imageURL", {}).get("small", "")
                    or act.get("imageURL", {}).get("large", "")
                )
                r1, r2 = st.columns([1, 3])
                with r1:
                    if img:
                        st.image(img, width=45)
                with r2:
                    st.markdown(
                        f"<span style='color:#f0f0f0'>{aname}</span> "
                        f"<span style='color:#ff4d8d;font-size:0.75rem'>"
                        f"ID:{aid}</span> ✅",
                        unsafe_allow_html=True,
                    )
            else:
                for act in results:
                    aid = str(act.get("id", ""))
                    aname = act.get("name", "不明")
                    img = (
                        act.get("imageURL", {}).get("small", "")
                        or act.get("imageURL", {}).get("large", "")
                    )
                    chk_c, img_c, info_c = st.columns([0.5, 1, 3])
                    with chk_c:
                        st.checkbox(
                            " ", key=f"chk_{aid}",
                            label_visibility="collapsed",
                        )
                    with img_c:
                        if img:
                            st.image(img, width=40)
                    with info_c:
                        st.markdown(
                            f"<span style='color:#f0f0f0'>{aname}</span> "
                            f"<span style='color:#ff4d8d;font-size:0.7rem'>"
                            f"ID:{aid}</span>",
                            unsafe_allow_html=True,
                        )
            st.markdown("---")

# ---------------------------------------------------------------------------
# メインヘッダー: タイトル + 編集ボタン
# ---------------------------------------------------------------------------
df_actresses = get_all_actresses()

hdr_left, hdr_right = st.columns([6, 1])
with hdr_left:
    st.markdown(
        '<h1 style="margin:0;padding:0;color:#f0f0f0;">AV Monitor</h1>',
        unsafe_allow_html=True,
    )
with hdr_right:
    if not df_actresses.empty:
        if st.button(
            "✏️ 編集" if not st.session_state.edit_mode else "✅ 完了",
            use_container_width=True,
        ):
            st.session_state.edit_mode = not st.session_state.edit_mode
            st.rerun()

st.markdown("---")

# ---------------------------------------------------------------------------
# メインコンテンツ
# ---------------------------------------------------------------------------
if df_actresses.empty:
    st.info("左上の ⌃ からサイドバーを開き、女優を追加してください。")
else:
    # グループ分類
    groups: dict[str, list] = {}
    group_order: list[str] = []
    for idx, row in df_actresses.iterrows():
        g = row["group"] if row["group"] else "未分類"
        if g not in groups:
            groups[g] = []
            group_order.append(g)
        groups[g].append({"row": row, "df_idx": idx})

    for eg in st.session_state.get("extra_groups", []):
        if eg not in groups:
            groups[eg] = []
            group_order.append(eg)

    # ========== 編集モード ==========
    if st.session_state.edit_mode:
        st.subheader("📝 編集")

        # --- 1) グループ順序の入れ替え ---
        st.markdown("#### 🔀 グループ順序")
        st.caption("⬆⬇ でグループの表示順を変更。変更後「💾 グループ順を保存」を押してください。")

        # セッションステートにグループ順序を保持
        if "edit_group_order" not in st.session_state:
            st.session_state.edit_group_order = list(group_order)

        ego = st.session_state.edit_group_order

        def _swap_groups(idx_a, idx_b):
            eo = st.session_state.edit_group_order
            eo[idx_a], eo[idx_b] = eo[idx_b], eo[idx_a]

        for gi, gname in enumerate(ego):
            gc1, gc2, gc3 = st.columns([6, 1, 1])
            with gc1:
                cnt = len(groups.get(gname, []))
                st.markdown(
                    f'<span style="color:#f0f0f0;font-weight:600">{gname}</span>'
                    f' <span style="color:#888;font-size:0.8rem">({cnt}人)</span>',
                    unsafe_allow_html=True,
                )
            with gc2:
                st.button(
                    "⬆", key=f"gup_{gi}",
                    disabled=(gi == 0),
                    on_click=_swap_groups,
                    args=(gi, gi - 1 if gi > 0 else gi),
                    use_container_width=True,
                )
            with gc3:
                st.button(
                    "⬇", key=f"gdn_{gi}",
                    disabled=(gi == len(ego) - 1),
                    on_click=_swap_groups,
                    args=(gi, gi + 1 if gi < len(ego) - 1 else gi),
                    use_container_width=True,
                )

        if st.button("💾 グループ順を保存", use_container_width=True, type="primary"):
            # グループ順序を反映させて全データ書き直し
            new_order = st.session_state.edit_group_order
            ws = get_sheet("actresses")
            records = ws.get_all_records()
            id_map = {}
            for r in records:
                id_map[str(r.get("actress_id", ""))] = r

            new_rows = []
            for gname in new_order:
                actual_g = gname if gname != "未分類" else ""
                for m in groups.get(gname, []):
                    aid = str(m["row"]["actress_id"])
                    if aid in id_map:
                        ir = id_map[aid]
                        new_rows.append([
                            ir.get("name", ""),
                            str(ir.get("actress_id", "")),
                            ir.get("image_url", ""),
                            actual_g,
                        ])

            ws.clear()
            ws.append_row(["name", "actress_id", "image_url", "group"])
            if new_rows:
                ws.append_rows(new_rows)
            _invalidate_actress_cache()
            st.session_state.pop("edit_group_order", None)
            st.success("グループ順を保存しました！")
            st.rerun()

        st.markdown("---")

        # --- 2) 女優の移動 (ドラッグ＆ドロップ) ---
        st.markdown("#### 🖐️ 女優の移動")
        st.caption(
            "女優をグループ間でドラッグして移動。"
            "変更後「💾 保存」を押してください。"
        )

        sortable_data = [
            {
                "header": g,
                "items": [
                    f'{m["row"]["name"]} [{m["row"]["actress_id"]}]'
                    for m in groups[g]
                ],
            }
            for g in group_order
        ]

        custom_css = """
        .sortable-component { border-radius: 10px; }
        .sortable-container {
            background: #141414; border-radius: 8px; margin-bottom: 8px;
            border: 1px solid #222;
        }
        .sortable-container-header {
            background: linear-gradient(90deg, #1a1a1a, #222);
            color: #f0f0f0;
            padding: 8px 12px; border-radius: 8px 8px 0 0; font-weight: 600;
        }
        .sortable-container-body { background: #141414; padding: 4px; }
        .sortable-item {
            background: #1e1e1e; color: #f0f0f0;
            border: 1px solid #333;
            border-radius: 6px; padding: 6px 10px; margin: 3px 0;
            font-size: 0.85rem; cursor: grab;
            transition: all 0.15s ease;
        }
        .sortable-item:hover {
            background: #2a2a2a;
            border-color: #ff4d8d;
        }
        """

        sorted_result = sort_items(
            sortable_data,
            multi_containers=True,
            direction="vertical",
            custom_style=custom_css,
        )

        if st.button("💾 並び順を保存", use_container_width=True, type="primary"):
            with st.spinner("保存中…"):
                save_actress_order(sorted_result)
                st.session_state.pop("extra_groups", None)
                st.session_state.pop("edit_group_order", None)
            st.success("並び順を保存しました！")
            st.rerun()

        st.markdown("---")

        # --- 3) グループ作成 (折りたたみ) ---
        with st.expander("➕ グループ作成", expanded=False):
            with st.form("new_group_form"):
                new_group_name = st.text_input(
                    "新しいグループ名", placeholder="例: お気に入り",
                    label_visibility="collapsed",
                )
                create_submitted = st.form_submit_button(
                    "作成", use_container_width=True
                )
            if create_submitted and new_group_name:
                if new_group_name in groups:
                    st.warning(f"「{new_group_name}」は既に存在します。")
                else:
                    if "extra_groups" not in st.session_state:
                        st.session_state.extra_groups = []
                    st.session_state.extra_groups.append(new_group_name)
                    st.rerun()

        # --- 4) グループ削除 (折りたたみ) ---
        with st.expander("🗑️ グループ削除", expanded=False):
            deletable = [g for g in group_order if g != "未分類"]
            if deletable:
                del_group = st.selectbox(
                    "削除するグループ", deletable,
                    label_visibility="collapsed",
                )
                if st.button(
                    f"「{del_group}」を削除",
                    use_container_width=True,
                ):
                    extras = st.session_state.get("extra_groups", [])
                    if del_group in extras:
                        extras.remove(del_group)
                    else:
                        with st.spinner("削除中…"):
                            ws = get_sheet("actresses")
                            records = ws.get_all_records()
                            for i, r in enumerate(records, start=2):
                                if str(r.get("group", "")) == del_group:
                                    ws.update_cell(i, 4, "")
                            _invalidate_actress_cache()
                    st.success(
                        f"「{del_group}」を削除しました。"
                    )
                    st.rerun()
            else:
                st.caption("削除可能なグループはありません。")

        # --- 5) 女優削除 (折りたたみ + 検索) ---
        with st.expander("🗑️ 女優削除", expanded=False):
            del_filter = st.text_input(
                "名前で検索", placeholder="名前を入力して絞り込み",
                key="del_actress_filter", label_visibility="collapsed",
            )
            filtered_rows = [
                row for _, row in df_actresses.iterrows()
                if not del_filter or del_filter in row["name"]
            ]
            if filtered_rows:
                for row_i, row in enumerate(filtered_rows):
                    if row_i > 0:
                        st.markdown(
                            '<hr style="margin:4px 0;border:none;'
                            'border-top:1px solid #333;">',
                            unsafe_allow_html=True,
                        )
                    c1, c2 = st.columns([6, 1])
                    with c1:
                        st.markdown(
                            f'<span style="color:#f0f0f0;font-size:0.9rem">'
                            f'{row["name"]}</span>',
                            unsafe_allow_html=True,
                        )
                    with c2:
                        if st.button("✕", key=f"del_{row['actress_id']}",
                                     use_container_width=True):
                            delete_actress(str(row["actress_id"]))
                            st.success(f"{row['name']} を削除しました。")
                            st.rerun()
            else:
                st.caption("該当する女優がいません。")

    # ========== 通常表示モード ==========
    else:
        st.session_state.pop("extra_groups", None)

        for g in group_order:
            members = groups[g]
            with st.expander(f"📂 {g}（{len(members)}人）", expanded=False):
                for i, member in enumerate(members):
                    actress = member["row"]
                    name = actress["name"]
                    actress_id = str(actress["actress_id"])
                    face_url = str(actress.get("image_url", ""))

                    render_actress_header(name, face_url)

                    try:
                        items = search_items_by_actress(actress_id, hits=30)
                        items = filter_items(items)
                    except Exception as e:
                        st.error(f"API エラー: {e}")
                        items = []

                    render_hscroll(items)
                    st.markdown("---")
