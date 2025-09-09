import asyncio
import logging
import logging.config
import os
import sys

from app.bot import main
from app.services.logger.logging_settings import logging_config

# Ensure stdout/stderr use UTF-8 to avoid UnicodeEncodeError on non-UTF locales
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    # Fallback silently if reconfigure isn't supported in the environment
    pass

logging.config.dictConfig(logging_config)

if sys.platform.startswith("win") or os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

asyncio.run(main())
