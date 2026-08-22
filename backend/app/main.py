from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_auth import router as auth_router
from app.api.routes_collect import router as collect_router
from app.api.routes_realtime import router as realtime_router
from app.api.routes_sites import router as sites_router
from app.api.routes_stats import router as stats_router
from app.api.routes_tracker import router as tracker_router
from app.api.routes_billing import router as billing_router
from app.api.routes_replay import router as replay_router
from app.core.config import settings
from app.core.database import create_tables



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create SQLite tables on startup
    create_tables()
    yield


app = FastAPI(title="Luminary Analytics Engine", lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if "https://luminary-web-event-engine.vercel.app" not in origins:
    origins.append("https://luminary-web-event-engine.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_pna_header(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response




app.include_router(auth_router)
app.include_router(collect_router)
app.include_router(sites_router)
app.include_router(stats_router)
app.include_router(realtime_router)
app.include_router(tracker_router)
app.include_router(billing_router)
app.include_router(replay_router)



@app.get("/health")
def health():
    return {"status": "ok"}