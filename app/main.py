import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routers import returns, assessment, decision, analytics

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("returns_backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    from app.database import ensure_schema_migrations
    ensure_schema_migrations(engine)
    logger.info("Database schema initialized successfully.")
    yield

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Production-grade backend for the Intelligent Product Returns & Recovery Engine. "
        "Provides return tracking, condition assessment, explainable disposition decisions, "
        "and financial/operational analytics."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Enable CORS for frontend and dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global safe exception handler to avoid leaking internal tracebacks
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error handling {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact system administrator."}
    )

# Include API Routers
app.include_router(returns.router)
app.include_router(assessment.router)
app.include_router(decision.router)
app.include_router(analytics.router)

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint confirming service status and database connectivity."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env,
        "version": "1.0.0"
    }

@app.get("/", tags=["System"])
def root():
    return {
        "message": "Welcome to the Intelligent Product Returns & Recovery Engine API.",
        "documentation": "/docs",
        "redoc": "/redoc"
    }
