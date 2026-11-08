from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app.models import Role, User
from app.routers import alerts, auth, dashboard, devices, jobs, users
from app.security import hash_password


def bootstrap_admin() -> None:
    from app.db import SessionLocal

    with SessionLocal() as db:
        if db.query(User).count() == 0:
            admin = User(
                username=settings.bootstrap_admin_user,
                email=settings.bootstrap_admin_email,
                hashed_password=hash_password(settings.bootstrap_admin_password),
                role=Role.admin,
            )
            db.add(admin)
            db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    bootstrap_admin()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for module in (auth, users, devices, jobs, alerts, dashboard):
        app.include_router(module.router)

    @app.get("/health")
    def health():
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
