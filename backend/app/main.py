import os
from fastapi import Request, Response
from slowapi.middleware import SlowAPIMiddleware
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import engine, SessionLocal, Base
from .models import User, Case, Offense
from .auth import hash_password, verify_password, create_access_token, check_password_strength, get_current_user, get_current_admin
from .detector import CyberbullyingSystem
from datetime import datetime, timedelta
from .schemas import MessageRequest
from .security_logger import logger
from dotenv import load_dotenv

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

app.add_middleware(SlowAPIMiddleware)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# -----------------------------
# Rate Limit Handler (with logging)
# -----------------------------
@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded from {request.client.host} at {request.url}")
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Try again later."},
    )

# -----------------------------
# Global HTTP Exception Logger
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

    
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    return response

# Create SQLAlchemy tables
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
# Root Route
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
        logger.warning(f"Weak password attempt for {username}")
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
        logger.info(f"Duplicate registration attempt for {username}")
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(username=username, password=hash_password(password))
    db.add(new_user)
    db.commit()

    logger.info(f"New user registered: {username}")

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
        logger.warning(f"Login attempt with non-existing user: {username}")
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if user.ban_until and datetime.utcnow() < user.ban_until:
        logger.warning(f"Banned user login attempt: {username}")
        remaining = user.ban_until - datetime.utcnow()
        hours = remaining.days * 24 + remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        raise HTTPException(status_code=403, detail=f"You are banned. Try again in {hours}h {minutes}m.")

    if user.lockout_until and datetime.utcnow() < user.lockout_until:
        logger.warning(f"Locked account login attempt: {username}")
        remaining = (user.lockout_until - datetime.utcnow()).seconds // 60
        raise HTTPException(status_code=403, detail=f"Account locked. Try again in {remaining} minutes.")

    if not verify_password(password, user.password):
        logger.warning(f"Failed login attempt for {username}")
        user.failed_attempts += 1

        if user.failed_attempts >= 5:
            logger.warning(f"Account locked for {username} due to multiple failed attempts")
            user.lockout_until = datetime.utcnow() + timedelta(minutes=15)
            user.failed_attempts = 0

        db.commit()
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user.failed_attempts = 0
    user.lockout_until = None
    db.commit()

    token = create_access_token({"sub": username})
    logger.info(f"Successful login for {username}")

    return {
        "access_token": token,
        "token_type": "bearer",
        "is_admin": user.is_admin
    }

# -----------------------------
# Analyze Route
# -----------------------------
@app.post("/analyze")
@limiter.limit("10/minute")
def analyze(request: Request, message: MessageRequest,
            current_user: str = Depends(get_current_user),
            db: Session = Depends(get_db)):

    user_id = current_user
    result = system.analyze_message(message.text, user_id, db)

    user = db.query(User).filter(User.username == user_id).first()
    warning_message = None

    # 🔥 THIS BLOCK MUST BE INDENTED INSIDE FUNCTION
    if result["risk_level"] == "severe":

        logger.warning(f"SEVERE risk message detected from {user_id}")

        user.warning_count += 1
        warning_message = f"You have {user.warning_count} warning(s). Further violations may result in ban."

        if user.warning_count >= 3:
            user.ban_until = datetime.utcnow() + timedelta(hours=48)
            logger.warning(f"User {user.username} banned until {user.ban_until}")
            warning_message = f"You are banned until {user.ban_until.strftime('%d %b %Y %I:%M %p')}"
            user.warning_count = 0

        db.commit()

    case = Case(user_id=user_id, text=message.text, severity=result["risk_level"])
    db.add(case)
    db.commit()

    response = result
    response["warning"] = warning_message

    return response   # ✅ MUST BE INSIDE FUNCTION
# -----------------------------
# Admin Routes
# -----------------------------
@app.get("/admin/users")
@limiter.limit("15/minute")
def get_all_users(request: Request,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_admin)):
    logger.info(f"Admin {current_user.username} accessed all users")
    return db.query(User).all()

@app.get("/admin/offenses")
@limiter.limit("15/minute")
def get_all_offenses(request: Request,
                     admin: User = Depends(get_current_admin),
                     db: Session = Depends(get_db)):
    logger.info(f"Admin {admin.username} accessed offenses")
    return db.query(Offense).all()

@app.get("/admin/cases")
@limiter.limit("15/minute")
def get_all_cases(request: Request,
                  admin: User = Depends(get_current_admin),
                  db: Session = Depends(get_db)):
    logger.info(f"Admin {admin.username} accessed cases")
    return db.query(Case).all()

@app.get("/admin/summary")
@limiter.limit("15/minute")
def admin_summary(request: Request,
                  admin: User = Depends(get_current_admin),
                  db: Session = Depends(get_db)):

    logger.info(f"Admin {admin.username} accessed summary")

    total_users = db.query(func.count(User.id)).scalar()
    total_cases = db.query(func.count(Case.id)).scalar()
    total_offenses = db.query(func.count(Offense.id)).scalar()

    active_lockouts = db.query(func.count(User.id))\
        .filter(User.lockout_until != None)\
        .scalar()

    return {
        "total_users": total_users,
        "total_cases": total_cases,
        "total_offenses": total_offenses,
        "active_lockouts": active_lockouts
    }
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html


# -----------------------------
# Admin Only Swagger Docs
# -----------------------------



