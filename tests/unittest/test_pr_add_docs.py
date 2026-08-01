from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pr_agent.tools.pr_add_docs import PRAddDocs, get_docs_for_language


def _make_add_docs(git_provider=None, prediction=None):
    add_docs = PRAddDocs.__new__(PRAddDocs)
    add_docs.git_provider = git_provider or MagicMock()
    add_docs.ai_handler = MagicMock()
    add_docs.token_handler = MagicMock()
    add_docs.patches_diff = None
    add_docs.prediction = prediction
    add_docs.cli_mode = False
    add_docs.vars = {"title": "a title", "diff": ""}
    return add_docs


def _settings(publish_output=True, verbosity_level=0):
    settings = MagicMock()
    settings.config.publish_output = publish_output
    settings.config.verbosity_level = verbosity_level
    settings.config.temperature = 0.2
    settings.pr_add_docs_prompt.system = "system {{ title }}"
    settings.pr_add_docs_prompt.user = "user {{ diff }}"
    return settings


def _diff_file(filename, head_file):
    return SimpleNamespace(filename=filename, head_file=head_file)


class TestGetDocsForLanguage:
    @pytest.mark.parametrize("language, expected", [
        ("java", "Javadocs"),
        ("Java", "Javadocs"),
        ("python", "Docstring (Google Style)"),
        ("lisp", "Docstring (Google Style)"),
        ("clojure", "Docstring (Google Style)"),
        ("javascript", "JSdocs"),
        ("TypeScript", "JSdocs"),
        ("c++", "Doxygen"),
        ("rust", "Docs"),
    ])
    def test_maps_language_to_documentation_flavor(self, language, expected):
        assert get_docs_for_language(language, "Google Style") == expected


class TestPreparePrCodeDocs:
    def test_wraps_a_bare_list_prediction_in_a_code_documentation_key(self):
        add_docs = _make_add_docs(prediction="- relevant file: a.py\n")

        assert add_docs._prepare_pr_code_docs() == {"Code Documentation": [{"relevant file": "a.py"}]}

    def test_keeps_a_mapping_prediction_as_is(self):
        add_docs = _make_add_docs(prediction="Code Documentation:\n- relevant file: a.py\n")

        assert add_docs._prepare_pr_code_docs() == {"Code Documentation": [{"relevant file": "a.py"}]}


class TestDedentCode:
    def test_indents_the_snippet_to_match_the_documented_line(self):
        git_provider = MagicMock()
        git_provider.diff_files = [_diff_file("a.py", "class A:\n    def f(self):\n        pass\n")]
        add_docs = _make_add_docs(git_provider)

        with patch("pr_agent.tools.pr_add_docs.get_settings", return_value=_settings()):
            snippet = add_docs.dedent_code("a.py", 2, '"""Docs."""', doc_placement="after",
                                           add_original_line=True)

        assert snippet == '    def f(self):\n        """Docs."""'

    def test_places_the_snippet_before_the_documented_line(self):
        git_provider = MagicMock()
        git_provider.diff_files = None
        git_provider.get_diff_files.return_value = [_diff_file("a.py", "    def f(self):\n        pass\n")]
        add_docs = _make_add_docs(git_provider)

        with patch("pr_agent.tools.pr_add_docs.get_settings", return_value=_settings()):
            snippet = add_docs.dedent_code("a.py", 1, "# Docs.", doc_placement="before",
                                           add_original_line=True)

        assert snippet == "    # Docs.\n    def f(self):"

    def test_returns_the_snippet_unchanged_for_an_unknown_file(self):
        git_provider = MagicMock()
        git_provider.diff_files = [_diff_file("b.py", "pass\n")]
        add_docs = _make_add_docs(git_provider)

        with patch("pr_agent.tools.pr_add_docs.get_settings", return_value=_settings()):
            assert add_docs.dedent_code("a.py", 1, '"""Docs."""') == '"""Docs."""'

    def test_returns_the_snippet_unchanged_when_the_line_is_out_of_range(self):
        git_provider = MagicMock()
        git_provider.diff_files = [_diff_file("a.py", "pass\n")]
        add_docs = _make_add_docs(git_provider)

        with patch("pr_agent.tools.pr_add_docs.get_settings", return_value=_settings(verbosity_level=2)):
            assert add_docs.dedent_code("a.py", 99, '"""Docs."""') == '"""Docs."""'


class TestPushInlineDocs:
    def test_publishes_a_suggestion_per_documented_line(self):
        git_provider = MagicMock()
        git_provider.publish_code_suggestions.return_value = True
        add_docs = _make_add_docs(git_provider)
        data = {"Code Documentation": [
            {"relevant file": " a.py ", "relevant line": "2", "documentation": '"""Docs."""',
             "doc placement": "after"},
        ]}

        with patch("pr_agent.tools.pr_add_docs.get_settings", return_value=_settings()), \
             patch.object(PRAddDocs, "dedent_code", return_value='"""Docs."""'):
            add_docs.push_inline_docs(data)

        git_provider.publish_code_suggestions.assert_called_once_with([{
            "body": '**Suggestion:** Proposed documentation\n```suggestion\n"""Docs."""\n```',
            "relevant_file": "a.py",
            "relevant_lines_start": 2,
            "relevant_lines_end": 2,
        }])

    def test_comments_when_there_is_nothing_to_document(self):
        git_provider = MagicMock()
        add_docs = _make_add_docs(git_provider)

        add_docs.push_inline_docs({"Code Documentation": []})

        git_provider.publish_comment.assert_called_once_with("No code documentation found to improve this PR.")
        git_provider.publish_code_suggestions.assert_not_called()

    def test_skips_malformed_entries(self):
        git_provider = MagicMock()
        git_provider.publish_code_suggestions.return_value = True
        add_docs = _make_add_docs(git_provider)
        data = {"Code Documentation": [{"relevant file": "a.py"}]}  # missing 'relevant line'

        with patch("pr_agent.tools.pr_add_docs.get_settings", return_value=_settings(verbosity_level=2)):
            add_docs.push_inline_docs(data)

        git_provider.publish_code_suggestions.assert_called_once_with([])

    def test_falls_back_to_publishing_suggestions_one_by_one(self):
        git_provider = MagicMock()
        git_provider.publish_code_suggestions.return_value = False
        add_docs = _make_add_docs(git_provider)
        data = {"Code Documentation": [
            {"relevant file": "a.py", "relevant line": "1", "documentation": "# A", "doc placement": "after"},
            {"relevant file": "b.py", "relevant line": "2", "documentation": "# B", "doc placement": "after"},
        ]}

        with patch("pr_agent.tools.pr_add_docs.get_settings", return_value=_settings()), \
             patch.object(PRAddDocs, "dedent_code", side_effect=["# A", "# B"]):
            add_docs.push_inline_docs(data)

        assert git_provider.publish_code_suggestions.call_count == 3  # one batch + one per suggestion
        assert [call.args[0][0]["relevant_file"]
                for call in git_provider.publish_code_suggestions.call_args_list[1:]] == ["a.py", "b.py"]


class TestPrediction:
    async def test_prepare_prediction_requests_a_numbered_diff(self):
        add_docs = _make_add_docs()

        with patch("pr_agent.tools.pr_add_docs.get_pr_diff", return_value="a diff") as mock_get_pr_diff, \
             patch.object(PRAddDocs, "_get_prediction", AsyncMock(return_value="Code Documentation: []")):
            await add_docs._prepare_prediction("gpt-4")

        assert mock_get_pr_diff.call_args.kwargs == {"add_line_numbers_to_hunks": True, "disable_extra_lines": False}
        assert add_docs.patches_diff == "a diff"
        assert add_docs.prediction == "Code Documentation: []"

    async def test_get_prediction_renders_prompts_with_the_diff(self):
        add_docs = _make_add_docs()
        add_docs.patches_diff = "a diff"
        add_docs.ai_handler.chat_completion = AsyncMock(return_value=("Code Documentation: []", "stop"))

        with patch("pr_agent.tools.pr_add_docs.get_settings", return_value=_settings(verbosity_level=2)):
            assert await add_docs._get_prediction("gpt-4") == "Code Documentation: []"

        kwargs = add_docs.ai_handler.chat_completion.call_args.kwargs
        assert kwargs["system"] == "system a title"
        assert kwargs["user"] == "user a diff"
        assert add_docs.vars["diff"] == "", "the original vars must not be mutated"


class TestRun:
    async def test_publishes_documentation_when_publish_output_enabled(self):
        git_provider = MagicMock()
        add_docs = _make_add_docs(git_provider)
        data = {"Code Documentation": [{"relevant file": "a.py"}]}

        with patch("pr_agent.tools.pr_add_docs.get_settings", return_value=_settings()), \
             patch("pr_agent.tools.pr_add_docs.retry_with_fallback_models", AsyncMock()), \
             patch.object(PRAddDocs, "_prepare_pr_code_docs", return_value=data), \
             patch.object(PRAddDocs, "push_inline_docs") as mock_push:
            await add_docs.run()

        git_provider.publish_comment.assert_called_once_with("Generating Documentation...", is_temporary=True)
        git_provider.remove_initial_comment.assert_called_once()
        mock_push.assert_called_once_with(data)

    async def test_does_nothing_when_the_model_returns_no_documentation(self):
        git_provider = MagicMock()
        add_docs = _make_add_docs(git_provider)

        with patch("pr_agent.tools.pr_add_docs.get_settings", return_value=_settings()), \
             patch("pr_agent.tools.pr_add_docs.retry_with_fallback_models", AsyncMock()), \
             patch.object(PRAddDocs, "_prepare_pr_code_docs", return_value={}), \
             patch.object(PRAddDocs, "push_inline_docs") as mock_push:
            await add_docs.run()

        mock_push.assert_not_called()
        git_provider.remove_initial_comment.assert_not_called()

    async def test_swallows_errors_raised_while_generating_documentation(self):
        add_docs = _make_add_docs()

        with patch("pr_agent.tools.pr_add_docs.get_settings", return_value=_settings()), \
             patch("pr_agent.tools.pr_add_docs.retry_with_fallback_models",
                   AsyncMock(side_effect=Exception("model failure"))):
            await add_docs.run()
