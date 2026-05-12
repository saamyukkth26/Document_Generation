import logging
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

# Configure root logger for the application
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("docgen")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "unknown"
        logger.info(f"Incoming request: {request.method} {request.url.path} from {client}")
        try:
            response = await call_next(request)
            logger.info(f"Response {response.status_code} for {request.method} {request.url.path}")
            return response
        except Exception as exc:
            logger.exception(f"Unhandled error while processing {request.method} {request.url.path}: {exc}")
            raise
from pydantic import BaseModel
import os
from .generator import ensure_template, generate_from_path

app = FastAPI(title="Document Generation Agent")
app.add_middleware(LoggingMiddleware)

# serve frontend static files (mounted at /)
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.isdir(static_dir):
    # Serve static assets under /static and serve index.html at /
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    from fastapi.responses import FileResponse

    @app.get("/")
    async def index():
        index_file = os.path.join(static_dir, "index.html")
        return FileResponse(index_file)


class GenerateRequest(BaseModel):
    path: str


@app.on_event("startup")
async def startup_event():
    ensure_template()


@app.post("/api/generate")
async def api_generate(req: GenerateRequest):
    path = req.path
    if not os.path.exists(path) or not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Path does not exist or is not a directory")
    out_path = await generate_from_path(path)
    return {"download_url": f"/download/{os.path.basename(out_path)}"}


@app.get("/download/{filename}")
async def download(filename: str):
    fpath = os.path.abspath(os.path.join("/tmp", filename))
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=fpath, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', filename=filename)
