# threads_fetch_my_postsv2.py
# 내 Threads 계정 전체 게시물 수집 → 정리 → CSV 저장 (Insights 옵션 포함)

import requests
import time
import pandas as pd
from datetime import datetime

# ==========================
# 설정 부분
# ==========================
ACCESS_TOKEN = "THAAHVf1dx4ZAtBUVMwdzN5UndSU295T3F5UUxCYTBUSkpKWTBHakxQdHhkbGpIMUxUQ3RQQm9yNmV6cGdsVnZAkcnhPbUZAGWTRESDl0ZAlpuSXROa0E3R3BSMEROZAm5ZAdU4zbEd6bXB4RlRIelRIcTcxWUZAsdlREMVQyS0ZAwaFo4M2NpZAwZDZD"  # 장기 액세스 토큰
THREADS_USER_ID = "24397979106496072"  # 필요 없으면 None으로 둬도 됨

# 👉 여기 숫자만 바꿔서 "최근 N개" 조절
TARGET_POST_COUNT = 10   # 예: 10개, 30개, 100개 ...

# Insights(조회수/좋아요/리플/리포스트/인용/공유)까지 뽑고 싶으면 True
# 토큰에 threads_manage_insights 권한이 없으면 False로 바꾸면 됨
ENABLE_INSIGHTS = True

BASE_URL = "https://graph.threads.net"

# Threads 포스트에서 가져올 필드들 (텍스트/타입/링크/시간 정도만 최소)
THREAD_FIELDS = ",".join([
    "id",
    "media_type",
    "media_url",
    "permalink",
    "username",
    "text",
    "timestamp",
    "topic_tag",
])


# ==========================
# 1) 내 계정 쓰레드 목록 가져오기 (최대 N개까지)
# ==========================
def fetch_posts(threads_user_id: str | None = None,
                limit_per_page: int = 50,
                max_pages: int = 50,
                max_posts: int | None = None):
    """
    내 계정의 쓰레드를 페이지네이션 돌면서 수집
    - threads_user_id 가 있으면 /{threads-user-id}/threads
    - 없으면 /me/threads 사용
    - max_posts: 총 몇 개까지 모을지 (None이면 끝까지)
    """
    if threads_user_id:
        url = f"{BASE_URL}/{threads_user_id}/threads"
    else:
        url = f"{BASE_URL}/me/threads"

    params = {
        "fields": THREAD_FIELDS,
        "limit": limit_per_page,
        "access_token": ACCESS_TOKEN,
    }

    all_posts = []
    page_count = 0

    while True:
        page_count += 1
        print(f"[INFO] Fetching page {page_count} ...")

        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            print("[ERROR] API Error:", resp.status_code, resp.text)
            break

        data = resp.json()
        posts = data.get("data", [])
        if not posts:
            break

        all_posts.extend(posts)

        # 👉 max_posts가 설정돼 있다면, 채워지면 바로 중단
        if max_posts is not None and len(all_posts) >= max_posts:
            all_posts = all_posts[:max_posts]
            print(f"[INFO] Reached max_posts={max_posts}, stop fetching.")
            break

        paging = data.get("paging", {})
        next_url = paging.get("next")
        if (not next_url) or (page_count >= max_pages):
            break

        # next_url에 이미 쿼리스트링 포함이므로 params 비움
        url = next_url
        params = {}

        # 너무 빠르게 요청 안 보내게 살짝 쉬기
        time.sleep(0.2)

    print(f"[INFO] Total posts fetched: {len(all_posts)}")
    return all_posts


# ==========================
# 2) 개별 쓰레드 Insights 가져오기 (조회수/좋아요/리플 등)
# ==========================
def fetch_insights(thread_id: str) -> dict:
    """
    /{threads-media-id}/insights?metric=views,likes,replies,reposts,quotes,shares
    형태로 호출해서 정량 지표를 반환
    """
    url = f"{BASE_URL}/{thread_id}/insights"
    params = {
        "metric": "views,likes,replies,reposts,quotes,shares",
        "access_token": ACCESS_TOKEN,
    }

    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print(f"[WARN] Insights error for {thread_id}: {resp.status_code} {resp.text}")
        return {}

    data = resp.json().get("data", [])
    metrics = {}
    for item in data:
        name = item.get("name")  # 예: "views", "likes", ...
        values = item.get("values") or []
        value = None
        if values:
            # 일반적으로 [{"value": 123, "end_time": "..."}] 형태
            v = values[0].get("value", 0)
            # 혹시 dict이면 대충 0 처리
            if isinstance(v, dict):
                v = 0
            value = v
        if name:
            metrics[name] = value

    return metrics


# ==========================
# 3) 정량 분석용으로 정리
# ==========================
def normalize_post(post: dict, insights: dict | None = None) -> dict:
    """
    Threads API raw post + Insights → 분석용 dict로 변환
    """
    text = post.get("text") or ""
    created_time = post.get("timestamp")

    # 해시태그 추출 (#으로 시작하는 단어)
    words = text.split()
    hashtags = [w for w in words if w.startswith("#")]

    # 시간 정보 파싱
    hour_of_day = None
    day_of_week = None
    if created_time:
        dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
        hour_of_day = dt.hour
        day_of_week = dt.weekday()  # 월=0, 일=6

    insights = insights or {}
    views = insights.get("views")
    likes = insights.get("likes")
    replies = insights.get("replies")
    reposts = insights.get("reposts")
    quotes = insights.get("quotes")
    shares = insights.get("shares")

    return {
        "post_id": post.get("id"),
        "created_time": created_time,
        "content": text,
        "content_length": len(text),
        "hashtag_count": len(hashtags),
        "hashtags": " ".join(hashtags),
        "media_type": post.get("media_type"),
        "media_url": post.get("media_url"),
        "permalink": post.get("permalink"),
        "username": post.get("username"),
        "topic_tag": post.get("topic_tag"),
        "hour_of_day": hour_of_day,
        "day_of_week": day_of_week,
        # Insights 기반 정량 지표
        "views": views,
        "likes": likes,
        "replies": replies,
        "reposts": reposts,
        "quotes": quotes,
        "shares": shares,
    }


# ==========================
# 4) 메인 실행부: 수집 → 정리 → CSV 저장
# ==========================
if __name__ == "__main__":
    # 1) 내 계정 쓰레드 가져오기 (최대 TARGET_POST_COUNT개)
    raw_posts = fetch_posts(
        THREADS_USER_ID,
        limit_per_page=50,
        max_pages=50,
        max_posts=TARGET_POST_COUNT,
    )

    rows = []
    for p in raw_posts:
        insights = {}
        if ENABLE_INSIGHTS:
            insights = fetch_insights(p.get("id"))
            # 너무 많이 호출하면 부담되니 약간 쉬어주기
            time.sleep(0.1)

        row = normalize_post(p, insights=insights)
        rows.append(row)

    if not rows:
        print("[WARN] 가져온 쓰레드가 없습니다. 토큰/권한/계정 연결을 다시 확인해 주세요.")

    df = pd.DataFrame(rows)

    output_path = "threads_my_posts_v2.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"[INFO] Saved to {output_path}")
    print(df.head())
