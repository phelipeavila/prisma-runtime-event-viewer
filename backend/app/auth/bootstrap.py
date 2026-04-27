import logging

from app.prisma.client import PrismaClient, PrismaAuthError
from app.state import AppState

logger = logging.getLogger("runtime_event_viewer.auth")


async def bootstrap(state: AppState) -> None:
    settings = state.settings
    if not settings.prisma_console_url:
        if settings.prisma_api_token or settings.prisma_api_key or settings.prisma_api_secret:
            logger.warning(
                "PRISMA_CONSOLE_URL is not set but auth credentials are present in env. "
                "Auth env vars will be ignored — provide the console URL via UI on first login."
            )
        else:
            logger.info("PRISMA_CONSOLE_URL not set — UI login required.")
        return

    state.token_store.set_console_url(settings.prisma_console_url)

    if settings.prisma_api_token:
        state.token_store.set_token(settings.prisma_api_token)
        logger.info("Authenticated from PRISMA_API_TOKEN env var.")
        return

    if settings.prisma_api_key and settings.prisma_api_secret:
        state.token_store.set_credentials(settings.prisma_api_key, settings.prisma_api_secret)
        client = PrismaClient(state.http, settings.prisma_console_url)
        try:
            token = await client.authenticate(
                settings.prisma_api_key, settings.prisma_api_secret
            )
            state.token_store.set_token(token)
            logger.info("Authenticated from PRISMA_API_KEY/SECRET env vars.")
        except PrismaAuthError as exc:
            logger.warning("Bootstrap auth failed: %s — UI login required.", exc)
        except Exception as exc:
            logger.warning("Bootstrap auth error: %s — UI login required.", exc)
        return

    logger.info("No auth env vars — UI login required.")
