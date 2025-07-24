import uvicorn

from application.app import get_app
from application.settings import ON_WINDOWS


app = get_app()

if __name__ == "__main__":
    uvicorn.run(
        app=app,
        port=8000,
        reload=False,
        loop="auto" if ON_WINDOWS else "uvloop"
    )
