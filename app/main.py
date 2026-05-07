from fastapi import FastAPI

from app.routers.ask import router as ask_router
from app.routers.docs import router as docs_router
from app.routers.health import router as health_router
from app.routers.search import router as search_router
from app.routers.upload import router as upload_router


app = FastAPI(title="my_first_rag", version="0.1.0")

app.include_router(health_router)
app.include_router(upload_router)
app.include_router(search_router)
app.include_router(ask_router)
app.include_router(docs_router)
