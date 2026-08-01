import pytest

from pr_agent.servers.help import HelpMessage

USAGE_GUIDES = [
    HelpMessage.get_review_usage_guide,
    HelpMessage.get_describe_usage_guide,
    HelpMessage.get_ask_usage_guide,
    HelpMessage.get_improve_usage_guide,
    HelpMessage.get_help_docs_usage_guide,
]


class TestGeneralHelpText:
    def test_commands_text_lists_every_supported_command(self):
        commands_text = HelpMessage.get_general_commands_text()

        for command in ["/review", "/describe", "/improve", "/ask", "/update_changelog",
                        "/help_docs", "/add_docs", "/generate_labels", "/config"]:
            assert f"**{command}" in commands_text or f"**{command}**" in commands_text

    def test_bot_help_text_wraps_the_commands_list(self):
        bot_help_text = HelpMessage.get_general_bot_help_text()

        assert bot_help_text.startswith("> To invoke the PR-Agent")
        assert HelpMessage.get_general_commands_text() in bot_help_text


class TestUsageGuides:
    @pytest.mark.parametrize("usage_guide", USAGE_GUIDES)
    def test_guide_starts_with_overview_and_links_to_docs(self, usage_guide):
        output = usage_guide()

        assert output.startswith("**Overview:**\n")
        assert "https://pr-agent-docs.codium.ai/tools/" in output

    @pytest.mark.parametrize("usage_guide, section", [
        (HelpMessage.get_review_usage_guide, "[pr_reviewer]"),
        (HelpMessage.get_describe_usage_guide, "[pr_description]"),
        (HelpMessage.get_improve_usage_guide, "[pr_code_suggestions]"),
    ])
    def test_guide_documents_its_own_configuration_section(self, usage_guide, section):
        assert section in usage_guide()

    def test_describe_guide_renders_collapsible_sections_and_general_help(self):
        output = HelpMessage.get_describe_usage_guide()

        assert output.count("<details>") == output.count("</details>")
        assert output.count("<tr><td>") == output.count("</td></tr>")
        assert "<table>" in output and "</table>" in output
        for summary in ["Enabling\\disabling automation", "Custom labels", "Utilizing extra instructions",
                        "More PR-Agent commands"]:
            assert summary in output
        assert HelpMessage.get_general_bot_help_text() in output

    def test_ask_and_help_docs_guides_show_their_invocation_syntax(self):
        assert '/ask "..."' in HelpMessage.get_ask_usage_guide()
        assert '/help_docs "..."' in HelpMessage.get_help_docs_usage_guide()
