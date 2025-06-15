from fastapi import FastAPI

from .api.routes import auth_routes, upload_routes
from .core.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(upload_routes.router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}
