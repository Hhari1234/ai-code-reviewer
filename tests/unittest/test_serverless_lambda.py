import pytest

# mangum is only installed in the serverless (AWS Lambda) deployment image.
pytest.importorskip("mangum")

from fastapi import APIRouter  # noqa: E402

from pr_agent.servers.serverless import build_lambda_handler  # noqa: E402


def test_build_lambda_handler_returns_mangum_handler():
    from mangum import Mangum

    handler = build_lambda_handler(APIRouter())
    assert isinstance(handler, Mangum)


@pytest.mark.parametrize("module_name", [
    "pr_agent.servers.github_lambda_webhook",
    "pr_agent.servers.gitlab_lambda_webhook",
])
def test_lambda_webhook_modules_expose_handler(module_name):
    import importlib

    module = importlib.import_module(module_name)
    assert callable(module.lambda_handler)
    from mangum import Mangum
    assert isinstance(module.handler, Mangum)
