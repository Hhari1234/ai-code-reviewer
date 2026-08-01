from unittest.mock import MagicMock, patch

import pytest

from pr_agent.tools.pr_config import PRConfig

CONFIGURATION_TOML = """\
[config]
model = "gpt-4"
publish_output = true

[pr_reviewer]
extra_instructions = ""
num_max_findings = 3

[github]
user_token = ""
"""


def _make_settings(tmp_path, settings_dict, skip_keys=None):
    conf_file = tmp_path / "configuration.toml"
    conf_file.write_text(CONFIGURATION_TOML)

    settings = MagicMock()
    settings.find_file.return_value = str(conf_file)
    settings.to_dict.return_value = settings_dict
    settings.config.get.return_value = skip_keys or []
    return settings


def _make_pr_config(git_provider=None):
    pr_config = PRConfig.__new__(PRConfig)
    pr_config.git_provider = git_provider or MagicMock()
    return pr_config


class TestPreparePrConfigs:
    def test_includes_only_pr_and_config_sections_present_in_configuration_file(self, tmp_path):
        settings = _make_settings(tmp_path, {
            "CONFIG": {"model": "gpt-4"},
            "PR_REVIEWER": {"num_max_findings": 3},
            "GITHUB": {"deployment_type": "user"},  # not a pr_/config section
            "PR_UNKNOWN": {"foo": "bar"},  # not present in configuration.toml
        })

        with patch("pr_agent.tools.pr_config.get_settings", return_value=settings):
            markdown_text = _make_pr_config()._prepare_pr_configs()

        assert "==================== CONFIG ====================" in markdown_text
        assert "==================== PR_REVIEWER ====================" in markdown_text
        assert "GITHUB" not in markdown_text
        assert "PR_UNKNOWN" not in markdown_text
        assert markdown_text.startswith("<details>")
        assert markdown_text.endswith("</details>\n")

    def test_renders_keys_lowercase_and_quotes_string_values(self, tmp_path):
        settings = _make_settings(tmp_path, {"CONFIG": {"Model": "gpt-4", "Verbosity_Level": 2}})

        with patch("pr_agent.tools.pr_config.get_settings", return_value=settings):
            markdown_text = _make_pr_config()._prepare_pr_configs()

        assert "config.model = 'gpt-4'" in markdown_text
        assert "config.verbosity_level = 2" in markdown_text

    @pytest.mark.parametrize("secret_key", [
        "ai_disclaimer",  # exact match on the skip list
        "PERSONAL_ACCESS_TOKEN",  # exact match, different case
        "webhook_signing_secret",  # partial match on 'secret'
        "deployment_private_data",  # partial match on 'private'
        "api_key_id",  # partial match on 'key'
    ])
    def test_skips_sensitive_keys(self, tmp_path, secret_key):
        settings = _make_settings(tmp_path, {"CONFIG": {secret_key: "sensitive", "model": "gpt-4"}})

        with patch("pr_agent.tools.pr_config.get_settings", return_value=settings):
            markdown_text = _make_pr_config()._prepare_pr_configs()

        assert "sensitive" not in markdown_text
        assert secret_key.lower() not in markdown_text
        assert "config.model = 'gpt-4'" in markdown_text

    def test_skips_extra_keys_from_config_skip_keys(self, tmp_path):
        settings = _make_settings(tmp_path, {"CONFIG": {"model": "gpt-4"}}, skip_keys=["model"])

        with patch("pr_agent.tools.pr_config.get_settings", return_value=settings):
            markdown_text = _make_pr_config()._prepare_pr_configs()

        assert "config.model" not in markdown_text

    def test_returns_empty_configs_when_configuration_file_cannot_be_loaded(self, tmp_path):
        settings = _make_settings(tmp_path, {"CONFIG": {"model": "gpt-4"}})
        settings.find_file.side_effect = Exception("no configuration.toml")

        with patch("pr_agent.tools.pr_config.get_settings", return_value=settings):
            markdown_text = _make_pr_config()._prepare_pr_configs()

        assert "config.model" not in markdown_text
        assert "```" in markdown_text


class TestRun:
    async def test_publishes_configs_when_publish_output_enabled(self, tmp_path):
        settings = _make_settings(tmp_path, {"CONFIG": {"model": "gpt-4"}})
        settings.config.publish_output = True
        git_provider = MagicMock()
        pr_config = _make_pr_config(git_provider)

        with patch("pr_agent.tools.pr_config.get_settings", return_value=settings):
            assert await pr_config.run() == ""

        published_comment = git_provider.publish_comment.call_args.args[0]
        assert "config.model = 'gpt-4'" in published_comment
        git_provider.remove_initial_comment.assert_called_once()

    async def test_does_not_publish_when_publish_output_disabled(self, tmp_path):
        settings = _make_settings(tmp_path, {"CONFIG": {"model": "gpt-4"}})
        settings.config.publish_output = False
        git_provider = MagicMock()
        pr_config = _make_pr_config(git_provider)

        with patch("pr_agent.tools.pr_config.get_settings", return_value=settings):
            assert await pr_config.run() == ""

        git_provider.publish_comment.assert_not_called()
        git_provider.remove_initial_comment.assert_not_called()
