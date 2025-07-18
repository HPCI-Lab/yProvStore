import uvicorn

from application.app import get_app
from application.settings import ON_WINDOWS


if __name__ == "__main__":
    uvicorn.run(
        app=get_app(),
        port=8000,
        reload=False,
        loop="auto" if ON_WINDOWS else "uvloop"
    )
