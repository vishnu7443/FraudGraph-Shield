import sys
import os

# Add the phase3 directory to the Python path so absolute imports in phase3 work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "phase3")))

try:
    from phase3.api.main import app
except Exception as e:
    import traceback
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI()
    
    error_traceback = traceback.format_exc()
    
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def catch_all(path: str):
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "traceback": error_traceback}
        )

