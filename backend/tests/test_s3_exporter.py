import importlib
import os
from datetime import datetime
from unittest.mock import patch


def test_exports_the_last_hour_once_per_event():
    with patch.dict(os.environ, {"TABLE_ARN": "table", "BUCKET_NAME": "bucket"}):
        index = importlib.import_module("s3_exporter.index")

    with patch.object(index, "client") as client:
        index.handler({"id": "event-1", "time": "2026-10-14T12:05:00Z"}, None)

    kwargs = client.export_table_to_point_in_time.call_args.kwargs
    # A retried invocation has the same event id, so it does not export again.
    assert kwargs["ClientToken"] == "event-1"
    assert kwargs["S3Prefix"] == "2026/10/14/12"
    assert kwargs["IncrementalExportSpecification"]["ExportFromTime"] == datetime(
        2026, 10, 14, 11
    )
