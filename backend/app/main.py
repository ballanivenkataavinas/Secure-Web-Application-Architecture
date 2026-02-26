import os
from fastapi import Request, Response
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
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

# -----------------------------
# Initialize App
# -----------------------------
app = FastAPI()
FRONTEND_URL = os.getenv("https://secure-web-application-architecture.vercel.app/")

if not FRONTEND_URL:
    raise ValueError("FRONTEND_URL not set")

app.add_middleware(SlowAPIMiddleware)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Try again later."},
    )

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://secure-web-application-architecture.vercel.app/"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

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
def register(
    request: Request,
    username: str,
    password: str,
    db: Session = Depends(get_db)
):

    if not username.endswith("@gmail.com"):
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

    new_user = User(
        username=username,
        password=hash_password(password)
    )

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
def login(
    request: Request,
    username: str,
    password: str,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if user.ban_until and datetime.utcnow() < user.ban_until:
        remaining = user.ban_until - datetime.utcnow()
        hours = remaining.days * 24 + remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60

        raise HTTPException(
            status_code=403,
            detail=f"You are banned. Try again in {hours}h {minutes}m."
        )

    if user.lockout_until and datetime.utcnow() < user.lockout_until:
        remaining = (user.lockout_until - datetime.utcnow()).seconds // 60
        raise HTTPException(
            status_code=403,
            detail=f"Account locked. Try again in {remaining} minutes."
        )

    if not verify_password(password, user.password):
        logger.warning(f"Failed login attempt for {username}")
        user.failed_attempts += 1

        if user.failed_attempts >= 5:
            user.lockout_until = datetime.utcnow() + timedelta(minutes=15)
            user.failed_attempts = 0

        db.commit()
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user.failed_attempts = 0
    user.lockout_until = None
    db.commit()

    token = create_access_token({"sub": username})

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
def analyze(
    request: Request,                     
    message: MessageRequest,              
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user

    result = system.analyze_message(message.text, user_id, db)

    user = db.query(User).filter(User.username == user_id).first()

    warning_message = None

    if result["risk_level"] == "HIGH":

        user.warning_count += 1
        warning_message = f"You have {user.warning_count} warning(s). Further violations may result in ban."

        if user.warning_count >= 3:
            user.ban_until = datetime.utcnow() + timedelta(hours=48)
            warning_message = f"You are banned until {user.ban_until.strftime('%d %b %Y %I:%M %p')}"
            user.warning_count = 0

        db.commit()

    case = Case(
        user_id=user_id,
        text=message.text,
        severity=result["risk_level"]
    )

    db.add(case)
    db.commit()

    response = result
    response["warning"] = warning_message

    return response

# -----------------------------
# Admin Routes
# -----------------------------
@app.get("/admin/users")
@limiter.limit("15/minute")
def get_all_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    logger.info(f"Admin {current_user.username} accessed all users")  
    return db.query(User).all()

@app.get("/admin/offenses")
@limiter.limit("15/minute")
def get_all_offenses(
    request: Request,                     
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return db.query(Offense).all()

@app.get("/admin/cases")
@limiter.limit("15/minute")
def get_all_cases(
    request: Request,                     
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return db.query(Case).all()

@app.get("/admin/summary")
@limiter.limit("15/minute")
def admin_summary(
    request: Request,                     
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):

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