from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.responses import Response, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import uvicorn
import logging 
from app.analysis import get_countries, plot_compare, VALID_METRICS
import os

# --- Security Setup ---
#Rate limiter (5 requests per minute per IP)
limiter = Limiter(key_func=get_remote_address)

# API Key header (for future auth)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Models for Input Validation ---
class CompareRequest(BaseModel):
    countries: str 
    metric: str = "pensions_pct_gdp"

    @field_validator('countries')
    def validate_countries(cls, v):
        # Remove whitespace and split
        country_list = [c.strip() for c in v.split(',')]
        if len(country_list) > 8:
            raise ValueError("Maximum 8 countries at a time")
        return v

    @field_validator('metric')
    def validate_metric(cls, v):
        if v not in VALID_METRICS:
            raise ValueError(f"Invalid metric. Choose from: {','.join(VALID_METRICS)}")
        return v

# Dependency to create the model
def get_compare_request(
        countries: str = Query(..., description="Comma-separated country codes"),
        metric: str = Query("pensions_pct_gdp", description="Metric to compare")
):
    return CompareRequest(countries=countries, metric=metric)


# --- FastAPI App ---
app = FastAPI(
    title="Pension Spending API",
    description="Secure API for European pension spending data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# --- Security Middleware
# 1. HTTPS Redirect (for production)
# Only enable HTTPS redirect in production (not when running locally)
if os.getenv("PRODUCTION", "false").lower() == "true":

    app.add_middleware(HTTPSRedirectMiddleware)

# 2. CORS (restrict to your domains)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://pension-api-qnn7.onrender.com/", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

# 3. Security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: blob: https://cdn.jsdelivr.net; "  # ✅ Added blob:
    "connect-src 'self' https://cdn.jsdelivr.net"  # ✅ Added connect-src
)
    return response

# --- Rate limiting ---
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later (~60sec)."},
        headers={"Retry-After": str(exc.retry_after)}
    )

# --- API Endpoints ---
@app.get("/")
@limiter.limit("5/minute")
async def root(request: Request):
    return RedirectResponse(url="/ui")

@app.get("/countries")
@limiter.limit("10/minute")
async def countries(request: Request):
    return get_countries()

@app.get("/plot/compare")
@limiter.limit("10/minute")
async def compare_plot(
    request: Request,
    params: CompareRequest = Depends(get_compare_request)
    
    #countries: str = Depends(CompareRequest),
    #metric: str = Depends(CompareRequest)
):
    """Generate comparison plot with validated input"""
    try:
        # Re-validate combined input
        #req = CompareRequest(countries, metric)
        png_data = plot_compare(params.countries, params.metric)
        return Response(content=png_data, media_type="image/png")
    except Exception as e:
        logger.error(f"Plot generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )

# --- UI ---
app.mount("/static", StaticFiles(directory="ui"), name="static")

@app.get("/ui", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def read_ui(request: Request):
    try:
        with open("ui/index.html", "r") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="UI not found")

# --- Main --- 
if __name__ == "__main__":
    # For development (HTTP). In production, use a reverse proxy with HTTPS.
    uvicorn.run(
        app, 
        host="0.0.0.0",
        port=8000
        # SSL options for direct HTTPS (not recommended for production)
        # ssl_keyfile="./key.pem",
        # ssl_certfile="./cert.pem"
    )

