import pandas as pd

UPLOAD_LOG_CSV = "zigcou_threads_upload_log.csv"   # 1단계 업로드 로그
THREADS_STATS_CSV = "threads_my_posts_v2.csv"      # 내 계정 전체 성과 데이터
OUTPUT_CSV = "master_for_annotation.csv"           # 프롬프트/본질 텍스트 입력용 최종 DF


def main():
    # 1) 업로드 로그 + Threads 성과 데이터 로드
    upload_df = pd.read_csv(UPLOAD_LOG_CSV)
    stats_df = pd.read_csv(THREADS_STATS_CSV)

    # 2) 공통 키(post_id) 만들기
    #    - 업로드 로그: threads_root_id -> post_id로 사용
    if "threads_root_id" not in upload_df.columns:
        raise KeyError("업로드 로그에 'threads_root_id' 컬럼이 없습니다. 업로드 코드에서 저장되도록 확인하세요.")

    upload_df["post_id"] = upload_df["threads_root_id"].astype(str)

    if "post_id" not in stats_df.columns:
        raise KeyError("Threads 성과 CSV에 'post_id' 컬럼이 없습니다. threads_fetch_my_posts.py 결과를 확인하세요.")

    stats_df["post_id"] = stats_df["post_id"].astype(str)

    # 3) post_id 기준으로 LEFT JOIN (업로드한 글 기준으로 성과 붙이기)
    master = pd.merge(
        upload_df,
        stats_df,
        on="post_id",
        how="left",
        suffixes=("_upload", "_stats"),
    )

    # 4) 프롬프트 / 본질 입력 칸 생성 (모두 텍스트)
    #    - 엑셀/스프레드시트에서 직접 작성할 필드
    master["prompt_text"] = ""   # 사용 프롬프트 전체 텍스트
    master["essence_text"] = ""  # 본질/핵심/패턴 설명 텍스트

    # 5) 보기 좋은 컬럼 순서로 정리 (실제 있는 컬럼만 사용)
    preferred_order = [
        # 공통 키
        "post_id",
        "threads_root_id",
        "threads_reply_id",

        # 직쿠/원본 쪽 정보 (실제 컬럼명에 맞게 조정)
        "link",
        "title",
        "content",
        "meme_text",
        "image",
        "affiliate_link",

        # 업로드 에러 로그
        "threads_error",

        # Threads 성과 쪽 정보 (threads_my_posts_v2.csv 기준)
        "permalink",
        "content_stats",      # threads_fetch_my_posts.py에서 content 컬럼명을 어떻게 썼는지에 따라 조정
        "created_time",
        "views",
        "likes",
        "replies",
        "reposts",
        "quotes",
        "shares",
        "media_type",
        "media_url",
        "username",
        "topic_tag",
        "hour_of_day",
        "day_of_week",
        "content_length",
        "hashtag_count",
        "hashtags",

        # 네가 직접 채울 텍스트 필드
        "prompt_text", 
        "essence_text",
    ]

    # 존재하는 컬럼만 순서대로 배치 + 나머지 컬럼은 뒤에 붙이기
    cols = [c for c in preferred_order if c in master.columns] + \
           [c for c in master.columns if c not in preferred_order]

    master = master[cols]

    # 6) CSV로 저장
    master.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"[INFO] 최종 분석용 DF 저장 완료: {OUTPUT_CSV}")
    print(master.head())


if __name__ == "__main__":
    main()
