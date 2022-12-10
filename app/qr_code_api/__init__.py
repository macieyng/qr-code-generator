import logging
import azure.functions as func

from main import app

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    """Each request is redirected to the ASGI handler."""
    return await func.AsgiMiddleware(app).handle_async(req, context)
