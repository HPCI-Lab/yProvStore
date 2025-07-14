import uvicorn
from application.app import get_app


if __name__ == "__main__":
    uvicorn.run(
        app=get_app(),
        port=8000,
        reload=False,
        loop="uvloop",
    )
