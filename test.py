from fastapi import FastAPI
from api.routes_health import router as health_router
from api.routes_algorithm import router as algo_router

app = FastAPI(title="Generic Python API Framework")

# 註冊所有 routes
app.include_router(health_router, prefix="/health")
app.include_router(algo_router, prefix="/algorithm")
