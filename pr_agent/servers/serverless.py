from fastapi import APIRouter, FastAPI
from mangum import Mangum
from starlette.middleware import Middleware
from starlette_context.middleware import RawContextMiddleware


def _apply_secrets_manager_config():
    try:
        from pr_agent.config_loader import apply_secrets_manager_config
        apply_secrets_manager_config()
    except Exception as e:
        try:
            from pr_agent.log import get_logger
            get_logger().debug(f"AWS Secrets Manager initialization failed, falling back to environment variables: {e}")
        except:
            # Fail completely silently if log module is not available
            pass


def build_lambda_handler(router: APIRouter):
    """Build a Mangum lambda handler for a webhook router.

    Wraps the router in a FastAPI app with RawContextMiddleware after loading any
    AWS Secrets Manager config, and returns the Mangum handler shared by the
    serverless webhook entrypoints.
    """
    _apply_secrets_manager_config()

    middleware = [Middleware(RawContextMiddleware)]
    app = FastAPI(middleware=middleware)
    app.include_router(router)

    return Mangum(app, lifespan="off")
