# threads_fetch_my_posts_incremental.py
# 내 Threads 계정 전체 게시물을 가져와서
# 기존 CSV와 합쳐 항상 최신 상태를 유지하는 수집기 + 인사이트 포함

import requests
import time
import pandas as pd
from datetime import datetime
from pathlib import Path

# ==========================
# 설정 부분
# ==========================
ACCESS_TOKEN = "YOUR_LONG_LIVED_TOKEN_HERE"   # 장기 액세스 토큰
THREADS_USER_ID = None  # None이면 /me/threads 기준. 필요하면 ID 넣어도 됨.

BASE_URL = "https://graph.threads.net/v1.0"
OUTPUT_CSV = Path("threads_my_posts_latest.csv")

THREAD_FIELDS = ",".join([
    "id",
    "media_product_type",
    "media_type",
    "media_url",
    "permalink",
    "owner",
    "username",
    "text",
    "timestamp",
    "shortcode",
    "thumbnail_url",
    "children",
    "is_quote_post",
])

# ==========================
# 기본 호출들
# ==========================
def debug_me():
    url = f"{BASE_URL}/me"
    params = {
        "fields": "id,username,name,threads_profile_picture_url,threads_biography",
        "access_token": ACCESS_TOKEN,
    }
    print("[DEBUG] Calling /me ...")
    resp = requests.get(url, params=params)
    print("[DEBUG] /me status:", resp.status_code)
    print("[DEBUG] /me response:", resp.text[:300], "...\n")
    return resp.status_code == 200


def fetch_all_posts(threads_user_id=None, limit_per_page=1000):
    if threads_user_id:
        url = f"{BASE_URL}/{threads_user_id}/threads"
    else:
        url = f"{BASE_URL}/me/threads"

    params = {
        "fields": THREAD_FIELDS,
        "limit": limit_per_page,
        "access_token": ACCESS_TOKEN,
    }

    print("[INFO] Fetching threads list ...")
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print("[ERROR] Threads list error:", resp.status_code, resp.text)
        return []

    data = resp.json()
    posts = data.get("data", [])
    print(f"[INFO] Total threads fetched from API: {len(posts)}")
    return posts


def fetch_insights(thread_id: str) -> dict:
    """
    /{thread_id}/insights?metric=views,likes,replies,reposts,quotes
    """
    url = f"{BASE_URL}/{thread_id}/insights"
    params = {
        "metric": "views,likes,replies,reposts,quotes",
        "access_token": ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print(f"[WARN] Insights error for {thread_id}: {resp.status_code} {resp.text}")
        return {}

    data = resp.json().get("data", [])
    metrics = {}
    for item in data:
        name = item.get("name")
        values = item.get("values") or []
        if not name or not values:
            continue
        v = values[0].get("value", 0)
        if isinstance(v, dict):
            v = 0
        metrics[name] = v

    return metrics


def normalize_post(post: dict, insights: dict | None = None) -> dict:
    text = post.get("text") or ""
    created_time = post.get("timestamp")

    words = text.split()
    hashtags = [w for w in words if w.startswith("#")]

    hour_of_day = None
    day_of_week = None
    if created_time:
        try:
            dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
            hour_of_day = dt.hour
            day_of_week = dt.weekday()
        except Exception:
            pass

    insights = insights or {}
    return {
        "post_id": post.get("id"),
        "created_time": created_time,
        "content": text,
        "content_length": len(text),
        "hashtag_count": len(hashtags),
        "hashtags": " ".join(hashtags),
        "media_type": post.get("media_type"),
        "media_product_type": post.get("media_product_type"),
        "media_url": post.get("media_url"),
        "permalink": post.get("permalink"),
        "username": post.get("username"),
        "shortcode": post.get("shortcode"),
        "is_quote_post": post.get("is_quote_post"),
        "hour_of_day": hour_of_day,
        "day_of_week": day_of_week,
        # 인사이트
        "views": insights.get("views"),
        "likes": insights.get("likes"),
        "replies": insights.get("replies"),
        "reposts": insights.get("reposts"),
        "quotes": insights.get("quotes"),
    }


def merge_with_existing(new_df: pd.DataFrame, path: Path) -> pd.DataFrame:
    if path.exists():
        old_df = pd.read_csv(path)
        print(f"[INFO] 기존 데이터 로드: {len(old_df)} rows")
    else:
        old_df = pd.DataFrame()

    if old_df.empty:
        return new_df

    merged = pd.merge(
        old_df,
        new_df,
        on="post_id",
        how="outer",
        suffixes=("_old", ""),
    )

    # 새 DF의 컬럼을 우선 적용, 없는 값은 old 사용
    for col in new_df.columns:
        if col == "post_id":
            continue
        col_old = col + "_old"
        if col in merged.columns and col_old in merged.columns:
            merged[col] = merged[col].where(merged[col].notna(), merged[col_old])

    drop_cols = [c for c in merged.columns if c.endswith("_old")]
    merged = merged.drop(columns=drop_cols)

    return merged


if __name__ == "__main__":
    ok = debug_me()
    if not ok:
        print("[WARN] /me 테스트 실패. 토큰/권한을 다시 확인하세요.\n")

    posts = fetch_all_posts(THREADS_USER_ID)

    rows = []
    for p in posts:
        insights = fetch_insights(p.get("id"))
        time.sleep(0.1)
        rows.append(normalize_post(p, insights=insights))

    new_df = pd.DataFrame(rows)
    print(f"[INFO] 새로 수집한 데이터 수: {len(new_df)}")

    merged_df = merge_with_existing(new_df, OUTPUT_CSV)
    merged_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"[INFO] 최종 저장 행 수: {len(merged_df)}")
    print(f"[INFO] Saved to {OUTPUT_CSV}")
