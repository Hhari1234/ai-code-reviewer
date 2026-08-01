from pr_agent.servers.gitlab_webhook import router
from pr_agent.servers.serverless import build_lambda_handler

handler = build_lambda_handler(router)


def lambda_handler(event, context):
    return handler(event, context)
