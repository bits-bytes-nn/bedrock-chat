import os

# Some modules create boto3 clients at import time, which needs a region. The tests
# that call AWS are marked with `aws` and are excluded by default.
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("DOCUMENT_BUCKET", "test-document-bucket")
