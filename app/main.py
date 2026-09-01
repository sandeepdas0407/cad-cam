from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes_files import router as files_router
from app.api.routes_index import router as index_router
from app.api.routes_search import router as search_router

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="CAD-CAM Document Search")

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))

app.include_router(index_router)
app.include_router(search_router)
app.include_router(files_router)


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
