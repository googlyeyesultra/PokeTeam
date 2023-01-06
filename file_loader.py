"""Provides a transparent interface between s3 and local files.
If the file exists locally, it loads that. Otherwise, it fetches it from S3.
It does so lazily, so that files which aren't needed aren't fetched."""

import boto3
import os
from botocore.exceptions import ClientError
from file_constants import DATA_DIR


class DataFilePath(os.PathLike):
    s3_session = boto3.session.Session(aws_access_key_id=os.environ["S3_ACCESS_KEY"],
                                       aws_secret_access_key=os.environ["S3_SECRET_KEY"])
    s3_bucket = s3_session.resource("s3", endpoint_url=os.environ["S3_ENDPOINT"]).Bucket(os.environ["BUCKET"])
    # TODO s3_bucket maybe should be a singleton?

    def __init__(self, filename):
        self.filename = filename
        
    def __fspath__(self):
        path = DATA_DIR + self.filename
        if os.path.exists(path):
            return path
        else:
            try:
                DataFilePath.s3_bucket.download_file(self.filename, path)
                return path
            except ClientError as e:
                raise FileNotFoundError(e)
