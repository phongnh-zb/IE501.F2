from pyspark.sql.functions import avg as _avg
from pyspark.sql.functions import col, count, countDistinct
from pyspark.sql.functions import floor as _floor
from pyspark.sql.functions import least as _least
from pyspark.sql.functions import lit, regexp_extract
from pyspark.sql.functions import sum as _sum
from pyspark.sql.functions import when

JOIN_KEYS = ["id_student", "code_module", "code_presentation"]

FORUM_TYPES    = ["forumng", "oucollaborate"]
QUIZ_TYPES     = ["quiz", "questionnaire", "externalquiz"]
RESOURCE_TYPES = ["resource", "url", "page", "oucontent", "pdf", "html_activity"]

FEATURE_FILL_ZERO = [
    "total_clicks", "active_days", "clicks_per_day",
    "forum_clicks", "quiz_clicks", "resource_clicks",
    "active_weeks", "engagement_ratio",
    "avg_score", "weighted_avg_score", "submission_rate", "avg_days_early",
    "exam_score", "tma_score", "cma_score",
    "withdrew_early", "days_before_start",
    "num_prev_attempts", "imd_band_encoded", "disability_encoded",
]


def _build_vle_features(df_vle, df_vle_info, df_courses):
    df_typed = df_vle.join(
        df_vle_info.select("id_site", "activity_type"),
        "id_site",
        "left",
    )

    df_agg = (
        df_typed
        .groupBy(*JOIN_KEYS)
        .agg(
            _sum("sum_click").alias("total_clicks"),
            countDistinct("date").alias("active_days"),
            # active_weeks — distinct 7-day periods with any engagement
            # VLE date is "days from module start", so floor(date/7) = week index
            countDistinct(_floor(col("date") / 7)).alias("active_weeks"),
            _sum(
                when(col("activity_type").isin(FORUM_TYPES), col("sum_click")).otherwise(0)
            ).alias("forum_clicks"),
            _sum(
                when(col("activity_type").isin(QUIZ_TYPES), col("sum_click")).otherwise(0)
            ).alias("quiz_clicks"),
            _sum(
                when(col("activity_type").isin(RESOURCE_TYPES), col("sum_click")).otherwise(0)
            ).alias("resource_clicks"),
        )
        .withColumn(
            "clicks_per_day",
            when(col("active_days") > 0, col("total_clicks") / col("active_days")).otherwise(0.0),
        )
    )

    # engagement_ratio — fraction of the module duration the student was active.
    # Clamped to 1.0 because students can interact with VLE materials before or
    # after the scheduled window, making active_days > module_presentation_length
    # a valid but > 100% outcome without the clamp.
    df_with_length = df_agg.join(
        df_courses.select("code_module", "code_presentation", "module_presentation_length"),
        ["code_module", "code_presentation"],
        "left",
    )

    return df_with_length.withColumn(
        "engagement_ratio",
        when(
            col("module_presentation_length").isNotNull() & (col("module_presentation_length") > 0),
            _least(col("active_days") / col("module_presentation_length"), lit(1.0)),
        ).otherwise(0.0),
    ).drop("module_presentation_length")


def _build_assessment_features(df_student_assess, df_assessments):
    # Filter banked assessments — is_banked=1 means the score was transferred
    # from a previous attempt and does not reflect current module performance.
    df_student_assess = df_student_assess.filter(col("is_banked") == 0)

    df_total_per_module = (
        df_assessments
        .groupBy("code_module", "code_presentation")
        .agg(count("id_assessment").alias("total_assessments"))
    )

    df_joined = df_student_assess.join(
        df_assessments.select(
            "id_assessment", "code_module", "code_presentation",
            "weight", "date", "assessment_type",
        ),
        "id_assessment",
        "left",
    )

    df_scores = (
        df_joined
        .groupBy(*JOIN_KEYS)
        .agg(
            _avg("score").alias("avg_score"),
            when(
                _sum("weight") > 0,
                _sum(col("score") * col("weight")) / _sum("weight"),
            ).otherwise(None).alias("weighted_avg_score"),
            count("id_assessment").alias("num_submitted"),
            _avg(
                when(col("date_submitted").isNotNull(), col("date") - col("date_submitted"))
            ).alias("avg_days_early"),
            _avg(when(col("assessment_type") == "Exam", col("score"))).alias("exam_score"),
            _avg(when(col("assessment_type") == "TMA",  col("score"))).alias("tma_score"),
            _avg(when(col("assessment_type") == "CMA",  col("score"))).alias("cma_score"),
        )
    )

    return (
        df_scores
        .join(df_total_per_module, ["code_module", "code_presentation"], "left")
        .withColumn(
            "submission_rate",
            when(
                col("total_assessments") > 0,
                col("num_submitted") / col("total_assessments"),
            ).otherwise(0.0),
        )
        .drop("total_assessments", "num_submitted")
    )


def _build_registration_features(df_reg):
    return df_reg.select(
        *JOIN_KEYS,
        when(col("date_unregistration").isNotNull(), lit(1)).otherwise(lit(0)).alias("withdrew_early"),
        when(
            col("date_registration").isNotNull(),
            (-col("date_registration")).cast("int"),
        ).otherwise(lit(0)).alias("days_before_start"),
    )


def _build_demographic_features(df_info):
    return (
        df_info
        .withColumn(
            "imd_band_encoded",
            (regexp_extract(col("imd_band"), r"(\d+)", 1).cast("int") / 10).cast("int"),
        )
        .withColumn(
            "disability_encoded",
            when(col("disability") == "Y", 1).otherwise(0),
        )
        .select(
            *JOIN_KEYS,
            col("num_of_prev_attempts").alias("num_prev_attempts"),
            "imd_band_encoded",
            "disability_encoded",
            col("gender"),
            col("region"),
            col("highest_education"),
            col("imd_band"),
            col("age_band"),
            col("studied_credits"),
            col("disability"),
            col("final_result"),
        )
    )


def _label_students(df_info):
    return df_info.withColumn(
        "label",
        when(col("final_result").isin("Pass", "Distinction"), 0).otherwise(1),
    )


def transform_data(df_info, df_vle, df_student_assess, df_assessments, df_reg, df_vle_info, df_courses):
    print(">>> [ETL:TRANSFORM] Building dropout label from final_result...")
    df_base = _label_students(df_info).select(*JOIN_KEYS, "label")

    print(">>> [ETL:TRANSFORM] Building VLE engagement features (8)...")
    df_vle_feats = _build_vle_features(df_vle, df_vle_info, df_courses)

    print(">>> [ETL:TRANSFORM] Building academic performance features (7)...")
    df_assess_feats = _build_assessment_features(df_student_assess, df_assessments)

    print(">>> [ETL:TRANSFORM] Building registration behavior features (2)...")
    df_reg_feats = _build_registration_features(df_reg)

    print(">>> [ETL:TRANSFORM] Building demographic features (3)...")
    df_demo_feats = _build_demographic_features(df_info)

    print(">>> [ETL:TRANSFORM] Joining all feature groups on (id_student, code_module, code_presentation)...")
    df_final = (
        df_base
        .join(df_vle_feats,    JOIN_KEYS, "left")
        .join(df_assess_feats, JOIN_KEYS, "left")
        .join(df_reg_feats,    JOIN_KEYS, "left")
        .join(df_demo_feats,   JOIN_KEYS, "left")
        .fillna(0, subset=FEATURE_FILL_ZERO)
    )

    row_count    = df_final.count()
    feature_cols = [c for c in FEATURE_FILL_ZERO if c in df_final.columns]
    n_groups     = len([_build_vle_features, _build_assessment_features,
                        _build_registration_features, _build_demographic_features])
    print(f">>> [ETL:TRANSFORM] Done — {row_count} rows, {len(feature_cols)} features across {n_groups} groups.")

    return df_final