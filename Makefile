%.parquet: %.tsv
		duckdb -c "COPY (SELECT * FROM read_csv('$<', delim = '	', header = true)) TO '$@' (FORMAT PARQUET)"

all: vocabulary_formats.parquet vocabulary_labels.parquet
