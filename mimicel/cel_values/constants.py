from datetime import datetime, timezone

# Timestamp の仕様上の範囲 (RFC3339 and CEL spec)
# "0001-01-01T00:00:00Z" to "9999-12-31T23:59:59.999999999Z"
# Pythonのdatetimeオブジェクトはnaiveでもawareでも作成できるが、比較や演算時はaware同士が推奨される。
# CELのTimestampは実質的にUTCとして扱われることが多い。
TIMESTAMP_MAX_DATETIME = datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)  # Pythonはマイクロ秒精度
TIMESTAMP_MIN_DATETIME = datetime(1, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
UINT64_MAX = 2 ** 64 - 1
INT64_MIN = -2 ** 63
INT64_MAX = 2 ** 63 - 1
