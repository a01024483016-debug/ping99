# threads_analysis_v2.py
# 내 Threads 계정 데이터(threads_my_posts_v2.csv) 기반 정량 패턴 분석기

import pandas as pd
import numpy as np
from textwrap import shorten

# ✅ 여기만 최신 CSV로 변경
INPUT_CSV = "threads_my_posts_v2.csv"

def print_section(title: str):
    print("\n" + "=" * 80)
    print(f"▶ {title}")
    print("=" * 80 + "\n")


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    if "views" in df.columns:
        df["views"] = df["views"].fillna(0)
    if "likes" in df.columns:
        df["likes"] = df["likes"].fillna(0)
    if "replies" in df.columns:
        df["replies"] = df["replies"].fillna(0)
    if "reposts" in df.columns:
        df["reposts"] = df["reposts"].fillna(0)
    if "quotes" in df.columns:
        df["quotes"] = df["quotes"].fillna(0)

    if "created_time" in df.columns:
        df["created_time_dt"] = pd.to_datetime(df["created_time"], errors="coerce")

    return df


# -----------------------------
# 1. 기본 통계 요약
# -----------------------------
def basic_summary(df: pd.DataFrame) -> dict:
    print_section("1. 기본 통계 요약")

    n_posts = len(df)
    print(f"- 전체 게시물 수: {n_posts}개")

    summary_info = {
        "total_posts": n_posts,
        "period_start": None,
        "period_end": None,
    }

    if "created_time_dt" in df.columns and df["created_time_dt"].notna().any():
        start = df["created_time_dt"].min()
        end = df["created_time_dt"].max()
        print(f"- 분석 기간: {start} ~ {end}")
        summary_info["period_start"] = start
        summary_info["period_end"] = end

    stats_dict = {}
    for col in ["views", "likes", "replies"]:
        if col in df.columns:
            print(f"\n[{col} 통계]")
            desc = df[col].describe()
            print(desc.to_string())
            stats_dict[col] = desc

    # CSV 저장용으로는 dict 대신 안 쓰고, 여기선 리턴만 해두자
    return summary_info, stats_dict


# -----------------------------
# 2. 시간대별 성과
# -----------------------------
def time_of_day_analysis(df: pd.DataFrame) -> pd.DataFrame | None:
    if "hour_of_day" not in df.columns:
        return None

    print_section("2. 시간대별 성과 (hour_of_day 기준)")

    grp = (
        df.groupby("hour_of_day")[["views", "likes", "replies"]]
        .mean()
        .round(2)
        .sort_index()
    )
    print(grp)

    if "views" in df.columns and len(grp) > 0:
        best_hour = grp["views"].idxmax()
        best_views = grp["views"].max()
        print(f"\n- 조회수 기준으로 가장 좋은 시간대: {best_hour}시 (평균 조회수: {best_views:.1f})")

    return grp


# -----------------------------
# 3. 요일별 성과
# -----------------------------
def day_of_week_analysis(df: pd.DataFrame) -> pd.DataFrame | None:
    if "day_of_week" not in df.columns:
        return None

    print_section("3. 요일별 성과 (day_of_week 기준)")

    day_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
    df = df.copy()
    df["day_name"] = df["day_of_week"].map(day_map)

    grp = (
        df.groupby("day_name")[["views", "likes", "replies"]]
        .mean()
        .round(2)
        .reindex(["월", "화", "수", "목", "금", "토", "일"])
    )

    print(grp)

    if "views" in df.columns and grp["views"].notna().any():
        best_day = grp["views"].idxmax()
        best_views = grp["views"].max()
        print(f"\n- 조회수 기준으로 가장 좋은 요일: {best_day}요일 (평균 조회수: {best_views:.1f})")

    return grp


# -----------------------------
# 4. 글 길이 구간별 성과
# -----------------------------
def content_length_bins_analysis(df: pd.DataFrame) -> pd.DataFrame | None:
    if "content_length" not in df.columns:
        return None

    print_section("4. 글 길이 구간별 성과 (content_length 기준)")

    df = df.copy()
    bins = [0, 80, 140, 200, 260, 10000]
    labels = ["~80자", "81~140자", "141~200자", "201~260자", "260자 이상"]

    df["length_bin"] = pd.cut(df["content_length"], bins=bins, labels=labels, right=True)

    grp = (
        df.groupby("length_bin")[["views", "likes", "replies"]]
        .mean()
        .round(2)
    )

    grp["count"] = df.groupby("length_bin")["post_id"].count()
    print(grp)

    if "views" in df.columns and grp["views"].notna().any():
        best_bin = grp["views"].idxmax()
        best_views = grp["views"].max()
        print(f"\n- 조회수 기준으로 가장 좋은 글 길이 구간: {best_bin} (평균 조회수: {best_views:.1f})")

    return grp


# -----------------------------
# 5. 해시태그 개수 구간별 성과
# -----------------------------
def hashtag_count_bins_analysis(df: pd.DataFrame) -> pd.DataFrame | None:
    if "hashtag_count" not in df.columns:
        return None

    print_section("5. 해시태그 개수 구간별 성과 (hashtag_count 기준)")

    df = df.copy()

    def hashtag_bin_func(x):
        if x == 0:
            return "0개"
        elif 1 <= x <= 2:
            return "1~2개"
        elif 3 <= x <= 5:
            return "3~5개"
        else:
            return "6개 이상"

    df["hashtag_bin"] = df["hashtag_count"].fillna(0).astype(int).map(hashtag_bin_func)

    grp = (
        df.groupby("hashtag_bin")[["views", "likes", "replies"]]
        .mean()
        .round(2)
    )
    grp["count"] = df.groupby("hashtag_bin")["post_id"].count()
    print(grp)

    if "views" in df.columns and grp["views"].notna().any():
        best_bin = grp["views"].idxmax()
        best_views = grp["views"].max()
        print(f"\n- 조회수 기준으로 가장 좋은 해시태그 개수 구간: {best_bin} (평균 조회수: {best_views:.1f})")

    return grp


# -----------------------------
# 6. 상위 게시물 리스트
# -----------------------------
def top_posts(df: pd.DataFrame, top_n: int = 10):
    print_section("6. 조회수/좋아요 상위 게시물 TOP 리스트")

    cols_to_show = ["post_id", "created_time", "views", "likes", "replies", "permalink", "content"]

    top_by_views = None
    top_by_likes = None

    if "views" in df.columns:
        print(f"[조회수 TOP {top_n}]")
        top_by_views = df.sort_values("views", ascending=False).head(top_n)[cols_to_show]
        for _, row in top_by_views.iterrows():
            print("-" * 60)
            print(f"조회수: {row['views']}, 좋아요: {row['likes']}, 댓글: {row['replies']}")
            print(f"시간: {row['created_time']}")
            print(f"링크: {row['permalink']}")
            preview = shorten(str(row["content"]).replace("\n", " "), width=80, placeholder="...")
            print(f"본문: {preview}")
        print()

    if "likes" in df.columns:
        print(f"\n[좋아요 TOP {top_n}]")
        top_by_likes = df.sort_values("likes", ascending=False).head(top_n)[cols_to_show]
        for _, row in top_by_likes.iterrows():
            print("-" * 60)
            print(f"좋아요: {row['likes']}, 조회수: {row['views']}, 댓글: {row['replies']}")
            print(f"시간: {row['created_time']}")
            print(f"링크: {row['permalink']}")
            preview = shorten(str(row["content"]).replace("\n", " "), width=80, placeholder="...")
            print(f"본문: {preview}")
        print()

    return top_by_views, top_by_likes


# -----------------------------
# 메인 실행 + CSV 저장
# -----------------------------
def main():
    df = load_data(INPUT_CSV)

    # 1) 기본 통계 (필요하면 나중에 따로 CSV로 빼도 됨)
    basic_summary(df)
    '''
    # 2) 시간대별 성과 → CSV
    time_df = time_of_day_analysis(df)
    if time_df is not None:
        time_df.to_csv("threads_analysis_time_of_day.csv", encoding="utf-8-sig")

    # 3) 요일별 성과 → CSV
    day_df = day_of_week_analysis(df)
    if day_df is not None:
        day_df.to_csv("threads_analysis_day_of_week.csv", encoding="utf-8-sig")

    # 4) 글 길이 구간별 성과 → CSV
    length_df = content_length_bins_analysis(df)
    if length_df is not None:
        length_df.to_csv("threads_analysis_content_length_bins.csv", encoding="utf-8-sig")

    # 5) 해시태그 개수 구간별 성과 → CSV
    hashtag_df = hashtag_count_bins_analysis(df)
    if hashtag_df is not None:
        hashtag_df.to_csv("threads_analysis_hashtag_bins.csv", encoding="utf-8-sig")
    '''
    # 6) TOP 게시물 → CSV
    top_by_views, top_by_likes = top_posts(df, top_n=10)
    if top_by_views is not None:
        top_by_views.to_csv("threads_analysis_top_by_views.csv", index=False, encoding="utf-8-sig")
    if top_by_likes is not None:
        top_by_likes.to_csv("threads_analysis_top_by_likes.csv", index=False, encoding="utf-8-sig")

    print("\n[INFO] 분석 결과 CSV 저장 완료 ✅")


if __name__ == "__main__":
    main()
