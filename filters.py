"""
filters.py − 共通フィルタリングロジック
=========================================
DMM API から取得した作品リストに対する除外フィルタ。
app.py / daily_notifier.py の両方からインポートして使う。
"""

import re

# ---------------------------------------------------------------------------
# 除外ルール定数
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


def filter_items(
    items: list[dict],
    *,
    max_items: int = MAX_ITEMS_PER_ACTRESS,
    require_sample_video: bool = False,
) -> list[dict]:
    """条件に合わない作品を除外して返す。

    Parameters
    ----------
    items : list[dict]
        DMM API ItemList のレスポンスアイテム。
    max_items : int
        返却の最大件数。
    require_sample_video : bool
        True の場合、sampleMovieURL が空の作品も除外する。
    """
    filtered: list[dict] = []
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

        if require_sample_video:
            sample = item.get("sampleMovieURL") or item.get("sampleImageURL")
            if not sample:
                continue

        filtered.append(item)
        if len(filtered) >= max_items:
            break
    return filtered
