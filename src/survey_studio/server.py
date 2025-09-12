"""FastAPI server setup for Survey Studio.

This module creates and configures the main FastAPI application with
all routers, middleware, and exception handlers.
"""

import subprocess
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from survey_studio.api.errors import (
    general_exception_handler,
    http_exception_handler,
    survey_studio_error_handler,
)
from survey_studio.api.routers import health, info, models, providers
from survey_studio.core.errors import SurveyStudioError


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Survey Studio API",
        description="AI-powered survey analysis and review service",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Add exception handlers
    app.add_exception_handler(SurveyStudioError, survey_studio_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # Include routers
    app.include_router(info.router, tags=["info"])
    app.include_router(health.router, tags=["health"])
    app.include_router(providers.router, tags=["providers"])
    app.include_router(models.router, tags=["models"])

    return app


# Create the app instance
app = create_app()

# Module path constant
APP_MODULE = "survey_studio.server:app"


def run_dev() -> None:
    """Run the development server with hot reload."""
    uvicorn.run(
        APP_MODULE,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
    )


def run_dev_no_reload() -> None:
    """Run the development server without hot reload."""
    uvicorn.run(
        APP_MODULE,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


def build_prod() -> None:
    """Build the application for production deployment."""
    print("Building production application...")

    # Install dependencies using Poetry (production only)
    subprocess.run(["poetry", "install", "--only=main"], check=True)

    # Run linting and formatting
    print("Running code quality checks...")
    subprocess.run(["poetry", "run", "ruff", "check", "--fix"], check=True)
    subprocess.run(["poetry", "run", "ruff", "format"], check=True)

    # Create a simple build info file
    date_result = subprocess.run(["date"], capture_output=True, text=True, check=False)
    poetry_result = subprocess.run(
        ["poetry", "--version"], capture_output=True, text=True, check=False
    )

    build_info = {
        "build_time": date_result.stdout.strip(),
        "python_version": sys.version,
        "poetry_version": poetry_result.stdout.strip(),
    }

    with open("build_info.txt", "w") as f:
        for key, value in build_info.items():
            f.write(f"{key}: {value}\n")

    print("Production build completed successfully!")
    print("Build info saved to build_info.txt")
    print("You can now run 'poetry run prod' to start the production server.")


def run_prod() -> None:
    """Run the production server."""
    uvicorn.run(
        APP_MODULE,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="warning",
        workers=1,  # For production, you might want to use multiple workers
    )


if __name__ == "__main__":
    run_dev()
