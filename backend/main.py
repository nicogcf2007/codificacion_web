"""CNC production entrypoint: durable v1 API, one worker."""
from modern.app import create_app

app = create_app()
api_app = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)