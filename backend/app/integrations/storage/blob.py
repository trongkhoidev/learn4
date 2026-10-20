from pathlib import Path

from app.core.config import settings


class BlobService:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not (settings.r2_endpoint_url and settings.r2_access_key_id and settings.r2_secret_access_key):
            self._client = False
            return False
        import boto3

        self._client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )
        return self._client

    def upload_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        client = self._get_client()
        if client is False:
            path = Path(settings.storage_dir) / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return f"/storage/{key}"
        client.put_object(Bucket=settings.r2_bucket, Key=key, Body=data, ContentType=content_type)
        return self.public_url(key)

    def upload_file(self, key: str, file_path: str | Path) -> str:
        return self.upload_bytes(key, Path(file_path).read_bytes())

    def public_url(self, key: str) -> str:
        if settings.r2_public_url:
            return f"{settings.r2_public_url.rstrip('/')}/{key}"
        return f"/storage/{key}"

    def delete(self, key: str) -> None:
        client = self._get_client()
        if client is False:
            path = Path(settings.storage_dir) / key
            path.unlink(missing_ok=True)
            return
        client.delete_object(Bucket=settings.r2_bucket, Key=key)

    def delete_blob(self, url: str) -> None:
        if not url:
            return
        key = url
        if url.startswith("local://"):
            key = url.replace("local://", "", 1)
        elif url.startswith("/storage/"):
            key = url.replace("/storage/", "", 1)
        elif settings.r2_public_url and url.startswith(settings.r2_public_url.rstrip('/')):
            key = url.replace(settings.r2_public_url.rstrip('/') + '/', "", 1)
        self.delete(key)


blob_service = BlobService()
