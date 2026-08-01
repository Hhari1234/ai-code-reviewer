from unittest.mock import MagicMock, patch

import pytest

from pr_agent.secret_providers.google_cloud_storage_secret_provider import \
    GoogleCloudStorageSecretProvider

SERVICE_ACCOUNT = '{"type": "service_account", "project_id": "some-project"}'


def _make_settings():
    settings = MagicMock()
    settings.google_cloud_storage.service_account = SERVICE_ACCOUNT
    settings.google_cloud_storage.bucket_name = "secrets-bucket"
    return settings


def _make_provider(bucket=None):
    provider = GoogleCloudStorageSecretProvider.__new__(GoogleCloudStorageSecretProvider)
    provider.client = MagicMock()
    provider.bucket_name = "secrets-bucket"
    provider.bucket = bucket or MagicMock()
    return provider


class TestInit:
    def test_builds_client_from_parsed_service_account_and_selects_bucket(self):
        client = MagicMock()
        with patch("pr_agent.secret_providers.google_cloud_storage_secret_provider.get_settings",
                   return_value=_make_settings()), \
             patch("pr_agent.secret_providers.google_cloud_storage_secret_provider.storage.Client") as mock_client_cls:
            mock_client_cls.from_service_account_info.return_value = client

            provider = GoogleCloudStorageSecretProvider()

        mock_client_cls.from_service_account_info.assert_called_once_with(
            {"type": "service_account", "project_id": "some-project"})
        assert provider.client is client
        assert provider.bucket_name == "secrets-bucket"
        client.bucket.assert_called_once_with("secrets-bucket")

    def test_raises_when_service_account_is_invalid(self):
        settings = _make_settings()
        settings.google_cloud_storage.service_account = "not-json"

        with patch("pr_agent.secret_providers.google_cloud_storage_secret_provider.get_settings",
                   return_value=settings), \
             patch("pr_agent.secret_providers.google_cloud_storage_secret_provider.storage.Client"):
            with pytest.raises(ValueError):
                GoogleCloudStorageSecretProvider()


class TestGetSecret:
    def test_downloads_blob_contents(self):
        bucket = MagicMock()
        bucket.blob.return_value.download_as_string.return_value = b"secret-value"

        assert _make_provider(bucket).get_secret("installation-42") == b"secret-value"
        bucket.blob.assert_called_once_with("installation-42")

    def test_returns_empty_string_when_download_fails(self):
        bucket = MagicMock()
        bucket.blob.return_value.download_as_string.side_effect = Exception("missing blob")

        assert _make_provider(bucket).get_secret("installation-42") == ""


class TestStoreSecret:
    def test_uploads_secret_value(self):
        bucket = MagicMock()

        _make_provider(bucket).store_secret("installation-42", "secret-value")

        bucket.blob.assert_called_once_with("installation-42")
        bucket.blob.return_value.upload_from_string.assert_called_once_with("secret-value")

    def test_raises_when_upload_fails(self):
        bucket = MagicMock()
        bucket.blob.return_value.upload_from_string.side_effect = Exception("permission denied")

        with pytest.raises(Exception, match="permission denied"):
            _make_provider(bucket).store_secret("installation-42", "secret-value")
