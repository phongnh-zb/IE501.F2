def load_to_hdfs(df, output_path, mode="overwrite", fmt="parquet"):
    print(f">>> [ETL:LOAD] Writing {fmt} to: {output_path} (mode={mode})")

    df.write.mode(mode).format(fmt).save(output_path)

    print(">>> [ETL:LOAD] Finished successfully!")