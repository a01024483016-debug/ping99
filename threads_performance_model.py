# threads_performance_model.py
# 내 Threads 계정 데이터 기반 "조회수 예측 모델" + 후보 글 스코어러

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
import joblib

DATA_PATH = Path("threads_my_posts_v1.csv")
MODEL_PATH = Path("model_threads_views.joblib")


FEATURE_COLS = ["content_length", "hashtag_count", "hour_of_day", "day_of_week", "is_text"]
TARGET_COL = "log_views"


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    # views 없는 건 0으로, 0인 건 학습에서 제외 (정보 없음)
    df["views"] = df["views"].fillna(0)
    df = df[df["views"] > 0].copy()

    # 로그 변환 (스케일 줄이기)
    df[TARGET_COL] = np.log1p(df["views"])

    # is_text 피처 생성
    df["is_text"] = (df["media_type"] == "TEXT_POST").astype(int)

    # 결측값 처리
    df["hashtag_count"] = df["hashtag_count"].fillna(0)
    df["content_length"] = df["content_length"].fillna(0)
    df["hour_of_day"] = df["hour_of_day"].fillna(0)
    df["day_of_week"] = df["day_of_week"].fillna(0)

    return df


def train_model(df: pd.DataFrame) -> RandomForestRegressor:
    X = df[FEATURE_COLS].values
    y = df[TARGET_COL].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=300,
        random_state=42,
        min_samples_leaf=2,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)

    print(f"[INFO] R2 (log_views 예측 성능): {r2:.3f}")
    print("[INFO] 피처 중요도:")
    for name, imp in sorted(
        zip(FEATURE_COLS, model.feature_importances_), key=lambda x: -x[1]
    ):
        print(f"  - {name}: {imp:.3f}")

    return model


def save_model(model: RandomForestRegressor, path: Path):
    joblib.dump(
        {
            "model": model,
            "feature_cols": FEATURE_COLS,
        },
        path,
    )
    print(f"[INFO] Model saved to {path}")


def load_model(path: Path):
    data = joblib.load(path)
    return data["model"], data["feature_cols"]


def predict_views_for_candidate(
    model: RandomForestRegressor,
    candidate: Dict,
) -> float:
    """
    candidate 예시:
    {
      "content_length": 120,
      "hashtag_count": 0,
      "hour_of_day": 16,
      "day_of_week": 6,  # 일요일
      "is_text": 1
    }
    """
    x = np.array([[candidate[col] for col in FEATURE_COLS]])
    log_pred = model.predict(x)[0]
    views_pred = float(np.expm1(log_pred))  # 로그 되돌리기
    return views_pred


def predict_for_multiple_candidates(
    model: RandomForestRegressor,
    candidates: List[Dict],
) -> List[Dict]:
    results = []
    for cand in candidates:
        pred = predict_views_for_candidate(model, cand)
        cand_with_pred = cand.copy()
        cand_with_pred["pred_views"] = round(pred, 1)
        results.append(cand_with_pred)
    return results


def demo_candidate_scoring(model):
    """
    예시: 서로 다른 설정 3가지를 비교해서 어느 게 잘 터질지 예측
    """
    candidates = [
        {
            "name": "A) 90자, 해시태그 0개, 일요일 16시, 텍스트",
            "content_length": 90,
            "hashtag_count": 0,
            "hour_of_day": 16,
            "day_of_week": 6,  # 일
            "is_text": 1,
        },
        {
            "name": "B) 150자, 해시태그 3개, 화요일 10시, 텍스트",
            "content_length": 150,
            "hashtag_count": 3,
            "hour_of_day": 10,
            "day_of_week": 1,  # 화
            "is_text": 1,
        },
        {
            "name": "C) 70자, 해시태그 1개, 수요일 13시, 텍스트",
            "content_length": 70,
            "hashtag_count": 1,
            "hour_of_day": 13,
            "day_of_week": 2,  # 수
            "is_text": 1,
        },
    ]

    scored = predict_for_multiple_candidates(model, candidates)
    scored_sorted = sorted(scored, key=lambda x: -x["pred_views"])

    print("\n[DEMO] 후보 설정별 예상 조회수 비교:")
    for c in scored_sorted:
        print(f"- {c['name']}: 예상 조회수 ≈ {c['pred_views']}")


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} not found. 먼저 threads_my_posts_v1.csv 를 생성해줘.")

    df = load_dataset(DATA_PATH)
    print(f"[INFO] 학습 데이터 수 (views>0): {len(df)}")

    model = train_model(df)
    save_model(model, MODEL_PATH)

    # 데모: 미리 정의한 후보 3개를 점수 매겨보기
    demo_candidate_scoring(model)


if __name__ == "__main__":
    main()
