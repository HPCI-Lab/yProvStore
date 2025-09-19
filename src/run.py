# Immediately configure logging so that all logs are captured
from application.logging_config.config import configure_logging
configure_logging()

import uvicorn  # noqa: E402
from dataclasses import asdict  # noqa: E402

from application.app import get_app  # noqa: E402
from application.settings import ON_WINDOWS  # noqa: E402
from application.logging_config.config import LogConfig  # noqa: E402


app = get_app()

if __name__ == "__main__":
    uvicorn.run(
        app=app,
        port=8000,
        reload=False,
        log_config=asdict(LogConfig()),
        loop="auto" if ON_WINDOWS else "uvloop"
    )
