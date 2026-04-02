from pyspark.sql.functions import avg as _avg
from pyspark.sql.functions import col
from pyspark.sql.functions import sum as _sum
from pyspark.sql.functions import when


def aggregate_clicks(df_vle):
    return df_vle.groupBy("id_student").agg(
        _sum("sum_click").alias("total_clicks")
    )


def aggregate_scores(df_assess):
    return df_assess.groupBy("id_student").agg(
        _avg("score").alias("avg_score")
    )


def label_students(df_info):
    return df_info.withColumn(
        "label",
        when(col("final_result").isin("Pass", "Distinction"), 0).otherwise(1),
    )


def transform_data(df_info, df_vle, df_assess):
    print(">>> [ETL:TRANSFORM] Aggregating clicks and scores...")
    df_clicks = aggregate_clicks(df_vle)
    df_scores = aggregate_scores(df_assess)

    print(">>> [ETL:TRANSFORM] Labeling students...")
    df_labeled = label_students(df_info)

    print(">>> [ETL:TRANSFORM] Joining tables...")
    df_final = (
        df_labeled
        .join(df_clicks, "id_student", "left")
        .join(df_scores, "id_student", "left")
        .fillna(0, subset=["total_clicks", "avg_score"])
    )

    row_count = df_final.count()
    print(f">>> [ETL:TRANSFORM] Done — {row_count} rows after join.")

    return df_final