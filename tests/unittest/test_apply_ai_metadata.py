import pr_agent.algo.pr_processing as pr_processing
from pr_agent.config_loader import get_settings


class FakeProvider:
    pass


def _set_config(monkeypatch, is_auto_command, enable_ai_metadata):
    settings = get_settings()
    monkeypatch.setattr(settings.config, "is_auto_command", is_auto_command, raising=False)
    monkeypatch.setattr(settings.config, "enable_ai_metadata", enable_ai_metadata, raising=False)
    return settings


def test_apply_ai_metadata_enriches_when_enabled(monkeypatch):
    calls = []
    monkeypatch.setattr(pr_processing, "add_ai_metadata_to_diff_files",
                        lambda provider, files: calls.append((provider, files)))
    _set_config(monkeypatch, is_auto_command=True, enable_ai_metadata=True)

    provider = FakeProvider()
    files = [{"full_file_name": "a.py"}]
    pr_processing.apply_ai_metadata_if_enabled(provider, files)

    assert calls == [(provider, files)]
    assert get_settings().get("config.enable_ai_metadata") is True


def test_apply_ai_metadata_disables_when_not_auto_command(monkeypatch):
    calls = []
    monkeypatch.setattr(pr_processing, "add_ai_metadata_to_diff_files",
                        lambda provider, files: calls.append((provider, files)))
    _set_config(monkeypatch, is_auto_command=False, enable_ai_metadata=True)

    pr_processing.apply_ai_metadata_if_enabled(FakeProvider(), [{"full_file_name": "a.py"}])

    assert calls == []
    assert get_settings().get("config.enable_ai_metadata") is False


def test_apply_ai_metadata_disables_when_no_description_files(monkeypatch):
    calls = []
    monkeypatch.setattr(pr_processing, "add_ai_metadata_to_diff_files",
                        lambda provider, files: calls.append((provider, files)))
    _set_config(monkeypatch, is_auto_command=True, enable_ai_metadata=True)

    pr_processing.apply_ai_metadata_if_enabled(FakeProvider(), [])

    assert calls == []
    assert get_settings().get("config.enable_ai_metadata") is False
