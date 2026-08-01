from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pr_agent.tools.pr_generate_labels import PRGenerateLabels


def _make_generate_labels(git_provider=None, prediction=None):
    generate_labels = PRGenerateLabels.__new__(PRGenerateLabels)
    generate_labels.git_provider = git_provider or MagicMock()
    generate_labels.pr_id = "owner/repo/1"
    generate_labels.ai_handler = MagicMock()
    generate_labels.token_handler = MagicMock()
    generate_labels.patches_diff = None
    generate_labels.prediction = prediction
    generate_labels.vars = {"title": "a title", "diff": ""}
    generate_labels.variables = {}
    return generate_labels


def _settings(publish_output=True):
    settings = MagicMock()
    settings.config.publish_output = publish_output
    settings.config.temperature = 0.2
    settings.config.enable_custom_labels = False
    settings.pr_description.extra_instructions = ""
    settings.pr_custom_labels_prompt.system = "system {{ title }}"
    settings.pr_custom_labels_prompt.user = "user {{ diff }}"
    return settings


class TestInit:
    def test_collects_pr_context_into_prompt_variables(self):
        git_provider = MagicMock()
        git_provider.pr.title = "a title"
        git_provider.get_pr_branch.return_value = "feature/labels"
        git_provider.get_pr_description.return_value = "a description"
        git_provider.get_commit_messages.return_value = "commit messages"
        git_provider.get_pr_id.return_value = "owner/repo/1"

        with patch("pr_agent.tools.pr_generate_labels.get_git_provider", return_value=lambda url: git_provider), \
             patch("pr_agent.tools.pr_generate_labels.get_main_pr_language", return_value="python"), \
             patch("pr_agent.tools.pr_generate_labels.TokenHandler") as mock_token_handler, \
             patch("pr_agent.tools.pr_generate_labels.get_settings", return_value=_settings()):
            generate_labels = PRGenerateLabels("https://example/pr/1", ai_handler=MagicMock)

        assert generate_labels.pr_id == "owner/repo/1"
        assert generate_labels.vars == {
            "title": "a title",
            "branch": "feature/labels",
            "description": "a description",
            "language": "python",
            "diff": "",
            "extra_instructions": "",
            "commit_messages_str": "commit messages",
            "enable_custom_labels": False,
            "custom_labels_class": "",
        }
        assert generate_labels.ai_handler.main_pr_language == "python"
        assert generate_labels.prediction is None
        mock_token_handler.assert_called_once()


class TestPrepareLabels:
    def test_returns_labels_given_as_a_list(self):
        generate_labels = _make_generate_labels()
        generate_labels.data = {"labels": ["Bug fix", "Tests"]}

        assert generate_labels._prepare_labels() == ["Bug fix", "Tests"]

    def test_splits_and_strips_labels_given_as_a_string(self):
        generate_labels = _make_generate_labels()
        generate_labels.data = {"labels": "Bug fix, Tests ,Documentation"}

        assert generate_labels._prepare_labels() == ["Bug fix", "Tests", "Documentation"]

    def test_returns_no_labels_when_prediction_has_no_labels_key(self):
        generate_labels = _make_generate_labels()
        generate_labels.data = {"other": "value"}

        assert generate_labels._prepare_labels() == []

    def test_restores_original_case_of_custom_labels(self):
        generate_labels = _make_generate_labels()
        generate_labels.data = {"labels": ["bug fix", "unmapped"]}
        generate_labels.variables = {"labels_minimal_to_labels_dict": {"bug fix": "Bug Fix"}}

        assert generate_labels._prepare_labels() == ["Bug Fix", "unmapped"]

    def test_keeps_labels_when_case_conversion_fails(self):
        generate_labels = _make_generate_labels()
        generate_labels.data = {"labels": ["Bug fix"]}
        generate_labels.variables = {"labels_minimal_to_labels_dict": None}

        assert generate_labels._prepare_labels() == ["Bug fix"]


@pytest.mark.asyncio
class TestPrediction:
    async def test_prepare_prediction_stores_diff_and_prediction(self):
        generate_labels = _make_generate_labels()

        with patch("pr_agent.tools.pr_generate_labels.get_pr_diff", return_value="a diff") as mock_get_pr_diff, \
             patch.object(PRGenerateLabels, "_get_prediction", AsyncMock(return_value="labels:\n- Bug fix")):
            await generate_labels._prepare_prediction("gpt-4")

        mock_get_pr_diff.assert_called_once_with(generate_labels.git_provider, generate_labels.token_handler, "gpt-4")
        assert generate_labels.patches_diff == "a diff"
        assert generate_labels.prediction == "labels:\n- Bug fix"

    async def test_get_prediction_renders_prompts_with_the_diff(self):
        generate_labels = _make_generate_labels()
        generate_labels.patches_diff = "a diff"
        generate_labels.ai_handler.chat_completion = AsyncMock(return_value=("labels:\n- Bug fix", "stop"))

        with patch("pr_agent.tools.pr_generate_labels.get_settings", return_value=_settings()), \
             patch("pr_agent.tools.pr_generate_labels.set_custom_labels") as mock_set_custom_labels:
            prediction = await generate_labels._get_prediction("gpt-4")

        assert prediction == "labels:\n- Bug fix"
        mock_set_custom_labels.assert_called_once_with(generate_labels.variables, generate_labels.git_provider)
        assert generate_labels.variables["diff"] == "a diff"
        assert generate_labels.vars["diff"] == "", "the original vars must not be mutated"
        kwargs = generate_labels.ai_handler.chat_completion.call_args.kwargs
        assert kwargs["system"] == "system a title"
        assert kwargs["user"] == "user a diff"


@pytest.mark.asyncio
class TestRun:
    async def test_publishes_generated_and_user_labels_when_provider_supports_labels(self):
        git_provider = MagicMock()
        git_provider.get_pr_labels.return_value = ["keep-me", "Enhancement"]
        git_provider.is_supported.return_value = True
        generate_labels = _make_generate_labels(git_provider, prediction="labels:\n- Bug fix")

        with patch("pr_agent.tools.pr_generate_labels.get_settings", return_value=_settings()), \
             patch("pr_agent.tools.pr_generate_labels.retry_with_fallback_models", AsyncMock()):
            assert await generate_labels.run() == ""

        git_provider.publish_labels.assert_called_once_with(["Bug fix", "keep-me"])
        git_provider.publish_comment.assert_called_once_with("Preparing PR labels...", is_temporary=True)
        git_provider.remove_initial_comment.assert_called_once()

    async def test_publishes_labels_as_a_comment_when_provider_does_not_support_labels(self):
        git_provider = MagicMock()
        git_provider.get_pr_labels.return_value = []
        git_provider.is_supported.return_value = False
        generate_labels = _make_generate_labels(git_provider, prediction="labels:\n- Bug fix")

        with patch("pr_agent.tools.pr_generate_labels.get_settings", return_value=_settings()), \
             patch("pr_agent.tools.pr_generate_labels.retry_with_fallback_models", AsyncMock()):
            await generate_labels.run()

        git_provider.publish_labels.assert_not_called()
        git_provider.publish_comment.assert_any_call("## PR Labels:\nBug fix\n", is_temporary=False)

    async def test_skips_publishing_when_publish_output_disabled(self):
        git_provider = MagicMock()
        generate_labels = _make_generate_labels(git_provider, prediction="labels:\n- Bug fix")

        with patch("pr_agent.tools.pr_generate_labels.get_settings", return_value=_settings(publish_output=False)), \
             patch("pr_agent.tools.pr_generate_labels.retry_with_fallback_models", AsyncMock()):
            await generate_labels.run()

        git_provider.publish_comment.assert_not_called()
        git_provider.publish_labels.assert_not_called()

    async def test_returns_none_without_an_ai_prediction(self):
        git_provider = MagicMock()
        generate_labels = _make_generate_labels(git_provider, prediction=None)

        with patch("pr_agent.tools.pr_generate_labels.get_settings", return_value=_settings()), \
             patch("pr_agent.tools.pr_generate_labels.retry_with_fallback_models", AsyncMock()):
            assert await generate_labels.run() is None

        git_provider.publish_labels.assert_not_called()

    async def test_swallows_errors_raised_while_generating_labels(self):
        generate_labels = _make_generate_labels(prediction="labels:\n- Bug fix")

        with patch("pr_agent.tools.pr_generate_labels.get_settings", return_value=_settings()), \
             patch("pr_agent.tools.pr_generate_labels.retry_with_fallback_models",
                   AsyncMock(side_effect=Exception("model failure"))):
            assert await generate_labels.run() == ""
