"""
AV Monitor - 新着チェック Web アプリ
=====================================
登録女優の新作（通販/予約情報）をDMM APIで検索し、
グループ別に横スクロールカードで一覧表示する。
サイドバー（デフォルト非表示）で女優の一括検索・追加、
編集モードでグループ管理が可能。
"""

import re
import uuid
import streamlit as st
import requests
import gspread
import pandas as pd
import urllib.parse
import feedparser
import time
from streamlit_sortables import sort_items
from oauth2client.service_account import ServiceAccountCredentials
from filters import filter_items

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
    /* Streamlit デプロイメニュー (Share/Star) を非表示 (サイドバーボタンは残す) */
    [data-testid="stDecoration"],
    .stDeployButton,
    [data-testid="stToolbar"] [data-testid="stToolbarActions"] {
        display: none !important;
    }
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
        overflow-y: visible;
        gap: 12px;
        padding: 8px 4px 20px;
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
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .icard:hover {
        transform: translateY(-4px);
        filter: brightness(1.1);
    }
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
# 定数（フィルタロジックは filters.py に統一済み）
# ---------------------------------------------------------------------------
MAX_ITEMS_PER_ACTRESS = 5

# ---------------------------------------------------------------------------
# セッションステート初期化
# ---------------------------------------------------------------------------
for key, default in {
    "search_results": {},       # name -> [actress dicts]
    "nh_search_results": {},    # name -> {articles, face_img}
    "search_error": "",
    "add_success": "",
    "edit_mode": False,
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
        sa = dict(st.secrets["gcp_service_account"])
        p_key = sa["private_key"].replace("\\n", "\n")
        sa["private_key"] = "\n".join([line.strip() for line in p_key.split("\n") if line.strip()])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(sa, SCOPES)
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


@st.cache_data(ttl=600, show_spinner=False)
def search_items_by_actress(actress_id: str, hits: int = 30):
    """API検索結果を10分間キャッシュ。ページリロードでも再取得しない。"""
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
    return resp.json().get("result", {}).get("items", [])


def make_item_url(content_id: str) -> str:
    return f"https://www.dmm.co.jp/mono/dvd/-/detail/=/cid={content_id}/"


# filter_items は filters.py からインポート済み


# ---------------------------------------------------------------------------
# NHブログ スクレイピングヘルパー
# ---------------------------------------------------------------------------
NH_BLOG_BASE = "https://main.av-somurie.xyz"
NH_BLOG_SEARCH_URL = NH_BLOG_BASE + "/?s={query}&feed=rss2"
NH_BLOG_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _nh_get(url: str) -> str:
    """User-Agent 付きで GET し、HTMLテキストを返す。"""
    resp = requests.get(url, headers={"User-Agent": NH_BLOG_UA}, timeout=60)
    resp.raise_for_status()
    return resp.text


def _fetch_rss(url: str) -> feedparser.FeedParserDict:
    """User-Agent 付きで RSS を取得し feedparser でパースして返す。"""
    resp = requests.get(url, headers={"User-Agent": NH_BLOG_UA}, timeout=30)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def search_nh_blog(actress_name: str) -> dict:
    """NHブログを検索し、女優のカテゴリパス・記事数を返す。
    戻り値: {category_path, articles: [{title, link, published}], count}
    category_path が空の場合は該当なし。"""
    url = NH_BLOG_SEARCH_URL.format(query=urllib.parse.quote(actress_name))
    feed = _fetch_rss(url)

    # 記事リンクからカテゴリパスを逆算
    # 例: https://main.av-somurie.xyz/tagyou/takanashi_kanon/post-57648/
    #   → category_path = "tagyou/takanashi_kanon"
    category_path = ""
    articles = []
    for entry in feed.entries:
        link = entry.get("link", "")
        title = entry.get("title", "")
        published = entry.get("published", "")
        # /actress_search/ は女優一覧ページなので除外
        if "/actress_search/" in link:
            continue
        
        # 記事リンクからカテゴリパスを抽出
        # 例: https://main.av-somurie.xyz/tagyou/takanashi_kanon/post-57648/
        m = re.match(r"https?://main\.av-somurie\.xyz/([\w]+/[\w]+)/post-\d+/?", link)
        if m:
            path = m.group(1)
            # URLのパスに、検索した女優名のローマ字読みなどが入っているか完全な一致判定は難しいが、
            # tagyou/takanashi_kanon のようなパスになっているはず。
            # 他の女優(nanami等)の単なる共演記事であればカテゴリパスが異なる。
            # よって最初の記事のカテゴリパスをその女優の専用カテゴリパスと見なす。
            # もしRSSの「カテゴリー」タグ等の情報で判別できるならそれが最善だが、
            # 現状は1番目に見つかった実際のカテゴリパスを信じて、それ以外は弾く。
            if not category_path:
                category_path = path

            # カテゴリパスが最初に確定したものと一致する記事だけを採用（別女優のカテゴリ記事を除外）
            if path == category_path:
                articles.append({
                    "title": title,
                    "link": link,
                    "published": published,
                })

    # さらに厳密に、取得した articles が本当にその女優向けか検証が必要なら行うが、
    # 基本的に名前検索でトップに出てくる一番多いカテゴリを採用するロジックにする
    if articles:
        # カテゴリ一覧の抽出とカウント
        path_counts = {}
        for entry in feed.entries:
            link = entry.get("link", "")
            if "/actress_search/" in link: continue
            m = re.match(r"https?://main\.av-somurie\.xyz/([\w]+/[\w]+)/post-\d+/?", link)
            if m:
                p = m.group(1)
                path_counts[p] = path_counts.get(p, 0) + 1
                
        # 一番出現頻度が高いカテゴリパスを正解とする
        if path_counts:
            best_path = max(path_counts, key=path_counts.get)
            category_path = best_path
            
            # best_path の記事だけ再収集
            articles = []
            for entry in feed.entries:
                link = entry.get("link", "")
                title = entry.get("title", "")
                published = entry.get("published", "")
                m = re.match(r"https?://main\.av-somurie\.xyz/([\w]+/[\w]+)/post-\d+/?", link)
                if m and m.group(1) == best_path:
                    articles.append({
                        "title": title,
                        "link": link,
                        "published": published,
                    })

    return {
        "category_path": category_path,
        "articles": articles,
        "count": len(articles),
    }


def _scrape_nh_face_img(category_path: str) -> str:
    """カテゴリページHTMLから顔画像URLのみを取得する。"""
    cat_url = f"{NH_BLOG_BASE}/category/{category_path}/"
    html = _nh_get(cat_url)
    profile_m = re.search(
        r'<article[^>]*class=["\'][^"\']*category-content[^"\']*["\'][^>]*>(.*?)</article>',
        html, re.DOTALL,
    )
    if profile_m:
        img_m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', profile_m.group(1))
        if img_m:
            return img_m.group(1)
    return ""


def _fetch_nh_category_rss(category_path: str, max_items: int = 5) -> list[dict]:
    """カテゴリ RSS から最新作品を取得する（軽量・高速）。
    戻り値: [{title, link, thumbnail, published}]"""
    rss_url = f"{NH_BLOG_BASE}/category/{category_path}/?feed=rss2"
    feed = _fetch_rss(rss_url)
    works = []
    for entry in feed.entries[:max_items]:
        title = entry.get("title", "")
        link = entry.get("link", "")
        
        # 投稿日時を FANZA と同じ YYYY-MM-DD HH:MM:SS 形式に揃える
        published_parsed = entry.get("published_parsed")
        if published_parsed:
            published = time.strftime('%Y-%m-%d %H:%M:%S', published_parsed)
        else:
            published = entry.get("published", "")

        # content:encoded や summary から画像を抽出
        content = ""
        if "content" in entry and entry.content:
            content = entry.content[0].get("value", "")
        if not content:
            content = entry.get("summary", "")
            
        imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content)
        
        thumb = ""
        # 1. pl.(jpg|webp|png) や top.jpg (パッケージ画像) を優先的に探す
        for img in imgs:
            if re.search(r'(?:pl|top)\.(?:jpg|jpeg|png|webp)', img, re.IGNORECASE):
                thumb = img
                break
                
        # 2. なければ、サンプル画像 (jp-X.jpg, -X.jpg, _X.jpg) および バナー画像 以外を探す
        if not thumb:
            for img in imgs:
                if not re.search(r'(?:jp-\d+|-\d+|_\d+)\.(?:jpg|jpeg|png|webp)|bannar', img, re.IGNORECASE):
                    thumb = img
                    break
                    
        # 3. それでもなければ最初の画像
        if not thumb and imgs:
            thumb = imgs[0]

        if title:
            works.append({
                "title": title,
                "link": link,
                "thumbnail": thumb,
                "published": published,
            })
    return works


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_nh_blog_items(category_path: str, max_items: int = 5) -> list[dict]:
    """NHブログ カテゴリRSS から最新作品を取得（1 時間キャッシュ）。
    戻り値: [{title, link, thumbnail, published}]
    例外時はキャッシュせず次回リトライ可能。"""
    return _fetch_nh_category_rss(category_path, max_items)


# ---------------------------------------------------------------------------
# スプシ操作ヘルパー
# ---------------------------------------------------------------------------
def get_all_actresses(force_refresh: bool = False) -> pd.DataFrame:
    if not force_refresh and "df_actresses_cache" in st.session_state:
        return st.session_state.df_actresses_cache
    ws = get_sheet("actresses")
    # ヘッダーに source 列がなければ自動追加
    header = ws.row_values(1)
    if "source" not in header:
        ws.update_cell(1, len(header) + 1, "source")
    records = ws.get_all_records()
    if not records:
        df = pd.DataFrame(columns=["name", "actress_id", "image_url", "group", "source"])
    else:
        df = pd.DataFrame(records)
        if "group" not in df.columns:
            df["group"] = ""
        df["group"] = df["group"].fillna("").astype(str)
        # source 列のフォールバック: 空欄は FANZA として扱う
        if "source" not in df.columns:
            df["source"] = "FANZA"
        df["source"] = df["source"].fillna("").astype(str)
        df["source"] = df["source"].replace("", "FANZA")
    st.session_state.df_actresses_cache = df
    return df


def _invalidate_actress_cache():
    st.session_state.pop("df_actresses_cache", None)
    _get_gspread_client.clear()


def add_actresses_batch(actress_list: list[tuple[str, str, str, str]]):
    """actress_list: [(name, actress_id, image_url, source), ...]"""
    ws = get_sheet("actresses")
    rows = [[name, str(aid), img, "", source] for name, aid, img, source in actress_list]
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
    ws.append_row(["name", "actress_id", "image_url", "group", "source"])
    if not df.empty:
        cols = ["name", "actress_id", "image_url", "group", "source"]
        for c in cols:
            if c not in df.columns:
                df[c] = "FANZA" if c == "source" else ""
        rows = df[cols].values.tolist()
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
                src = str(r.get("source", "")) or "FANZA"
                new_rows.append([
                    r.get("name", ""),
                    str(r.get("actress_id", "")),
                    r.get("image_url", ""),
                    actual_group,
                    src,
                ])

    ws.clear()
    ws.append_row(["name", "actress_id", "image_url", "group", "source"])
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
            collected.append((act.get("name", name), aid, img, "FANZA"))
        else:
            for act in results:
                aid = str(act.get("id", ""))
                if st.session_state.get(f"chk_{aid}", False):
                    img = (
                        act.get("imageURL", {}).get("small", "")
                        or act.get("imageURL", {}).get("large", "")
                    )
                    collected.append((act.get("name", name), aid, img, "FANZA"))
    if collected:
        try:
            add_actresses_batch(collected)
            names = ", ".join(c[0] for c in collected)
            st.session_state.add_success = names
            st.session_state.search_results = {}
            st.session_state.pending_names = ""
        except Exception as e:
            st.session_state.search_error = f"追加失敗: {e}"


def _cb_swap(df, idx_a, idx_b):
    swap_actress_order(df, idx_a, idx_b)
    search_items_by_actress.clear()


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


def render_hscroll_blog(items: list[dict]):
    """NHブログ作品をカード型で横スクロール表示する。"""
    if not items:
        st.caption("作品なし")
        return

    cards = []
    for item in items:
        title = item.get("title", "タイトル不明")
        url = item.get("link", "#")
        thumb = item.get("thumbnail", "")
        date = item.get("published", "")[:10]
        img_tag = f'<img src="{thumb}" loading="lazy">' if thumb else ""
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

    # 情報元トグル
    search_source = st.radio(
        "情報元",
        ["FANZA公式", "NH"],
        horizontal=True,
        key="search_source_radio",
    )

    with st.form("multi_search_form", clear_on_submit=True):
        query = st.text_area(
            "女優名（カンマ区切り）",
            placeholder="深田えいみ, 三上悠亜, 橋本ありな",
            height=80,
        )
        submitted = st.form_submit_button("検索", use_container_width=True)

    if submitted and query:
        names = parse_names(query)
        if search_source == "FANZA公式":
            # --- FANZA 検索 (既存ロジック) ---
            old_results = dict(st.session_state.search_results)
            errors = []
            for name in names:
                if name in old_results:
                    continue
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
        else:
            # --- NH検索 (プレビュー→選択方式) ---
            old_nh = dict(st.session_state.nh_search_results)
            errors = []
            for name in names:
                if name in old_nh:
                    continue
                try:
                    result = search_nh_blog(name)
                    cat_path = result.get("category_path", "")
                    articles = result.get("articles", [])
                    if cat_path and articles:
                        # カテゴリページから顔画像を取得
                        try:
                            face_img = _scrape_nh_face_img(cat_path)
                        except Exception:
                            face_img = ""
                        old_nh[name] = {
                            "category_path": cat_path,
                            "articles": articles,
                            "face_img": face_img,
                            "count": len(articles),
                        }
                    else:
                        errors.append(f"「{name}」: 記事が見つかりません")
                except Exception as e:
                    errors.append(f"「{name}」: {e}")
            st.session_state.nh_search_results = old_nh
            if errors:
                st.session_state.search_error = " / ".join(errors)
        st.rerun()

    # --- 蓄積された結果表示 (FANZA検索結果) ---
    if st.session_state.search_results:
        all_results = st.session_state.search_results
        st.markdown(f"**🔍 FANZA検索結果: {len(all_results)}名**")

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

    # --- 蓄積された結果表示 (NH検索結果) ---
    if st.session_state.nh_search_results:
        nh_results = st.session_state.nh_search_results
        st.markdown(f"**🔍 NH検索結果: {len(nh_results)}名**")

        def _cb_nh_batch_add():
            """NH検索結果から全女優を一括登録する。"""
            collected = []
            for name, data in st.session_state.nh_search_results.items():
                # actress_id にカテゴリパスを保存 (例: tagyou/takanashi_kanon)
                aid = data.get("category_path", f"nhb-{uuid.uuid4().hex[:12]}")
                face_img = data.get("face_img", "")
                collected.append((name, aid, face_img, "NH_BLOG"))
            if collected:
                try:
                    add_actresses_batch(collected)
                    names_str = ", ".join(c[0] for c in collected)
                    st.session_state.add_success = names_str
                    st.session_state.nh_search_results = {}
                except Exception as e:
                    st.session_state.search_error = f"追加失敗: {e}"

        st.button(
            "✅ まとめて登録",
            use_container_width=True, type="primary",
            on_click=_cb_nh_batch_add, key="nh_batch_add_btn",
        )

        if st.button("🗑️ NH検索結果をクリア", use_container_width=True,
                     key="nh_clear_btn"):
            st.session_state.nh_search_results = {}
            st.rerun()

        for search_name, data in nh_results.items():
            face_img = data.get("face_img", "")
            count = data.get("count", 0)
            r1, r2 = st.columns([1, 3])
            with r1:
                if face_img:
                    st.image(face_img, width=45)
            with r2:
                st.markdown(
                    f"<span style='color:#f0f0f0;font-weight:600'>"
                    f"{search_name}</span> "
                    f"<span style='color:#ff4d8d;font-size:0.75rem'>"
                    f"({count}件の記事)</span> ✅",
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
                        src = str(ir.get("source", "")) or "FANZA"
                        new_rows.append([
                            ir.get("name", ""),
                            str(ir.get("actress_id", "")),
                            ir.get("image_url", ""),
                            actual_g,
                            src,
                        ])

            ws.clear()
            ws.append_row(["name", "actress_id", "image_url", "group", "source"])
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
                        if st.button("✕", key=f"del_{row_i}_{row['actress_id']}",
                                     use_container_width=True):
                            delete_actress(str(row["actress_id"]))
                            st.success(f"{row['name']} を削除しました。")
                            st.rerun()
            else:
                st.caption("該当する女優がいません。")

    # ========== 通常表示モード ==========
    else:
        st.session_state.pop("extra_groups", None)

        # --- 全女優のデータを1回で取得＆フィルタ (高速化) ---
        filtered_cache: dict[str, list[dict]] = {}      # FANZA 用
        blog_cache: dict[str, list[dict]] = {}            # NHブログ用
        for g in group_order:
            for member in groups[g]:
                actress_id = str(member["row"]["actress_id"]).replace(".0", "").strip()
                source = str(member["row"].get("source", "")) or "FANZA"
                if source == "NH_BLOG":
                    if actress_id not in blog_cache:
                        try:
                            blog_cache[actress_id] = fetch_nh_blog_items(actress_id)
                        except Exception:
                            blog_cache[actress_id] = []
                else:
                    if actress_id not in filtered_cache:
                        try:
                            raw = search_items_by_actress(actress_id, hits=30)
                            filtered_cache[actress_id] = filter_items(
                                raw, require_sample_video=True,
                            )
                        except Exception:
                            filtered_cache[actress_id] = []
                            
        # --- 🔥 新着ピックアップ (全女優から最新10本) ---
        all_latest: list[dict] = []
        nh_latest: list[dict] = []
        for g in group_order:
            for member in groups[g]:
                actress = member["row"]
                actress_id = str(actress["actress_id"]).replace(".0", "").strip()
                source = str(actress.get("source", "")) or "FANZA"
                if source == "NH_BLOG":
                    for it in blog_cache.get(actress_id, []):
                        entry = {
                            "title": it.get("title", ""),
                            "date": it.get("published", ""),
                            "content_id": "",
                            "_link": it.get("link", ""),
                            "_thumbnail": it.get("thumbnail", ""),
                            "_actress_name": actress["name"],
                            "_source": "NH_BLOG",
                        }
                        nh_latest.append(entry)
                else:
                    for it in filtered_cache.get(actress_id, []):
                        entry = {**it, "_actress_name": actress["name"], "_source": "FANZA"}
                        all_latest.append(entry)

        # FANZA の新着ソートと重複除去
        all_latest.sort(key=lambda x: x.get("date", ""), reverse=True)
        seen_keys: set[str] = set()
        unique_latest: list[dict] = []
        for it in all_latest:
            key = it.get("content_id", "")
            if key and key not in seen_keys:
                seen_keys.add(key)
                unique_latest.append(it)
            if len(unique_latest) >= 10:
                break
                
        # NH の新着ソートと重複除去 (投稿日ベース)
        nh_latest.sort(key=lambda x: x.get("date", ""), reverse=True)
        seen_nh_keys: set[str] = set()
        unique_nh_latest: list[dict] = []
        for it in nh_latest:
            key = it.get("_link", "")
            if key and key not in seen_nh_keys:
                seen_nh_keys.add(key)
                unique_nh_latest.append(it)
            if len(unique_nh_latest) >= 10:
                break

        if unique_latest:
            st.markdown(
                '<h3 style="color:#f0f0f0;margin-bottom:4px;">'
                '🔥 新着ピックアップ (FANZA)</h3>',
                unsafe_allow_html=True,
            )
            st.caption("登録女優の最新作品")
            cards = []
            for item in unique_latest:
                title = item.get("title", "タイトル不明")
                aname = item.get("_actress_name", "")
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
                    f'  <div class="dt">📅 {date}　👤 {aname}</div>'
                    f"</a>"
                )
            st.markdown(
                '<div class="hscroll">' + "".join(cards) + "</div>",
                unsafe_allow_html=True,
            )
            st.markdown("---")
            
        # --- グループ別一覧 (キャッシュ再利用) ---
        for g in group_order:
            # NHグループならば、その直前にNH向け新着ピックアップを配置する
            if g == "NH" and unique_nh_latest:
                st.markdown(
                    '<h3 style="color:#f0f0f0;margin-bottom:4px;">'
                    '🔥 新着ピックアップ (NH)</h3>',
                    unsafe_allow_html=True,
                )
                st.caption("NHブログの最新記事")
                cards = []
                for item in unique_nh_latest:
                    title = item.get("title", "タイトル不明")
                    aname = item.get("_actress_name", "")
                    date = item.get("date", "")[:10]
                    url = item.get("_link", "#")
                    img = item.get("_thumbnail", "")
                    img_tag = f'<img src="{img}" loading="lazy">' if img else ""
                    cards.append(
                        f'<a class="icard" href="{url}" target="_blank">'
                        f"  {img_tag}"
                        f'  <div class="ttl">{title}</div>'
                        f'  <div class="dt">📅 {date}　👤 {aname}</div>'
                        f"</a>"
                    )
                st.markdown(
                    '<div class="hscroll">' + "".join(cards) + "</div>",
                    unsafe_allow_html=True,
                )
                st.markdown("---")

            members = groups[g]
            with st.expander(f"📂 {g}（{len(members)}人）", expanded=False):
                for i, member in enumerate(members):
                    actress = member["row"]
                    name = actress["name"]
                    actress_id = str(actress["actress_id"]).replace(".0", "").strip()
                    face_url = str(actress.get("image_url", ""))
                    source = str(actress.get("source", "")) or "FANZA"

                    if source == "NH_BLOG":
                        render_actress_header(name, face_url)
                        items = blog_cache.get(actress_id, [])
                        render_hscroll_blog(items)
                    else:
                        render_actress_header(name, face_url)
                        items = filtered_cache.get(actress_id, [])
                        render_hscroll(items)
                    st.markdown("---")


