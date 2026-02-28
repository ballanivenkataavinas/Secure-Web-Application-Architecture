import os
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.middleware import SlowAPIMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from dotenv import load_dotenv

from .database import engine, SessionLocal, Base
from .models import User, Case, Offense, RefreshToken, AuditLog
from .auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,   # ✅ FIXED IMPORT
    check_password_strength,
    get_current_user,
    get_current_admin
)
from .detector import CyberbullyingSystem
from .schemas import MessageRequest
from .security_logger import logger

# -----------------------------
# Initialize App
# -----------------------------
app = FastAPI(
    title="Cyberbully AI API",
    version="1.0.0"
)

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL")
if not FRONTEND_URL:
    raise ValueError("FRONTEND_URL environment variable not set")

# -----------------------------
# Rate Limiter Setup
# -----------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# -----------------------------
# Rate Limit Handler
# -----------------------------
@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded from {request.client.host} at {request.url}")
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Try again later."},
    )

# -----------------------------
# HTTP Exception Logger
# -----------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        logger.warning(f"Unauthorized access attempt at {request.url}")
    elif exc.status_code == 403:
        logger.warning(f"Forbidden access attempt at {request.url}")
    elif exc.status_code == 400:
        logger.info(f"Bad request at {request.url}")

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# -----------------------------
# Global Server Error Logger
# -----------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error at {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# -----------------------------
# Security Headers
# -----------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://fastapi.tiangolo.com;"
    )

    return response

# -----------------------------
# Payload Size Limit
# -----------------------------
@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    max_size = 1024 * 10  # 10KB
    body = await request.body()

    if len(body) > max_size:
        raise HTTPException(status_code=413, detail="Payload too large")

    return await call_next(request)

# -----------------------------
# Audit Middleware
# -----------------------------
@app.middleware("http")
async def audit_middleware(request: Request, call_next):

    response = await call_next(request)

    # Log only admin endpoints
    if request.url.path.startswith("/admin"):

        db = SessionLocal()
        try:
            ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")

            db.add(AuditLog(
                user="unknown",  # can upgrade to real user later
                action="ADMIN_ACCESS",
                endpoint=request.url.path,  # cleaner than full URL
                ip_address=ip,
                user_agent=user_agent
            ))

            db.commit()

        finally:
            db.close()

    return response

# -----------------------------
# Create Tables
# -----------------------------
Base.metadata.create_all(bind=engine)

system = CyberbullyingSystem()

# -----------------------------
# Database Dependency
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------
# Root
# -----------------------------
@app.get("/")
def root():
    return {"message": "Cyberbully AI API Running (DSA Engine Active)"}

# -----------------------------
# Register
# -----------------------------
@app.post("/register")
@limiter.limit("3/minute")
def register(request: Request, username: str, password: str, db: Session = Depends(get_db)):

    if not username.endswith("@gmail.com"):
        logger.warning(f"Invalid registration attempt: {username}")
        raise HTTPException(status_code=400, detail="Only Gmail accounts allowed")

    strength, feedback = check_password_strength(password)

    if strength == "weak":
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Weak password",
                "strength": strength,
                "suggestions": feedback
            }
        )

    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(username=username, password=hash_password(password))
    db.add(new_user)
    db.commit()

    return {
        "message": "User registered successfully",
        "password_strength": strength
    }

# -----------------------------
# Login
# -----------------------------
@app.post("/login")
@limiter.limit("5/minute")
def login(request: Request, username: str, password: str, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(password, user.password):
        user.failed_attempts += 1
        if user.failed_attempts >= 5:
            user.lockout_until = datetime.utcnow() + timedelta(minutes=15)
            user.failed_attempts = 0
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user.failed_attempts = 0
    user.lockout_until = None
    db.commit()

    access_token = create_access_token({"sub": username})
    refresh_token, expiry = create_refresh_token(username)

    db_refresh = RefreshToken(
        token=refresh_token,
        user_id=username,
        expires_at=expiry
    )

    db.add(db_refresh)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "is_admin": user.is_admin
    }

# -----------------------------
# Refresh Token
# -----------------------------
@app.post("/refresh")
def refresh(refresh_token: str, db: Session = Depends(get_db)):

    stored = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token,
        RefreshToken.revoked == False
    ).first()

    if not stored or stored.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access = create_access_token({"sub": stored.user_id})
    return {"access_token": new_access}

# -----------------------------
# Analyze
# -----------------------------
@app.post("/analyze")
@limiter.limit("10/minute")
def analyze(request: Request,
            message: MessageRequest,
            current_user: str = Depends(get_current_user),
            db: Session = Depends(get_db)):

    result = system.analyze_message(message.text, current_user, db)

    case = Case(
        user_id=current_user,
        text=message.text,
        severity=result["risk_level"]
    )

    db.add(case)
    db.commit()

    return result

# -----------------------------
# Admin Routes
# -----------------------------
@app.get("/admin/users")
def get_all_users(db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_admin)):
    return db.query(User).all()

@app.get("/admin/offenses")
def get_all_offenses(db: Session = Depends(get_db),
                     admin: User = Depends(get_current_admin)):
    return db.query(Offense).all()

@app.get("/admin/cases")
def get_all_cases(db: Session = Depends(get_db),
                  admin: User = Depends(get_current_admin)):
    return db.query(Case).all()

@app.get("/admin/summary")
def admin_summary(db: Session = Depends(get_db),
                  admin: User = Depends(get_current_admin)):

    return {
        "total_users": db.query(func.count(User.id)).scalar(),
        "total_cases": db.query(func.count(Case.id)).scalar(),
        "total_offenses": db.query(func.count(Offense.id)).scalar()
    }

@app.get("/admin/audit-logs")
def get_audit_logs(db: Session = Depends(get_db),
                   admin: User = Depends(get_current_admin)):

    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()