from pathlib import Path
import time
import os
from fastapi import FastAPI, Request, Depends, Form, Body, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from itsdangerous import URLSafeSerializer
import uvicorn
from typing import cast
import math
import calculator  # new module in d:\api\calculator.py
import random

from db import engine, SessionLocal, Base
import models
import auth
from sqlalchemy.orm import Session
from schemas import UserCreate, Token, UserOut

BASE_DIR = Path(__file__).parent.resolve()
SECRET_KEY = "change_this_to_a_random_secret_in_production"

# simple in-memory user store used by the template-based auth paths (can be left empty or populated at runtime)
USERS = {}

# replace bcrypt-based context with pbkdf2_sha256-only to avoid bcrypt dependency
pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
serializer = URLSafeSerializer(SECRET_KEY, salt="session")

app = FastAPI()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def add_custom_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Cache-busting version for static assets (updates on server start)
app.state.asset_version = str(int(time.time()))
# Toggle login bypass via env; default ON per user request (set BYPASS_LOGIN=0 to disable)
app.state.bypass_login = (os.getenv("BYPASS_LOGIN", "1").lower() in ("1", "true", "yes", "on"))
# Backend URL for frontend to use (empty means use relative URLs)
app.state.backend_url = os.getenv("BACKEND_URL", "")

# create tables and apply lightweight SQLite migrations for added columns
# Use Base from db.py to create tables; avoid reassigning models.Base which breaks model definitions
Base.metadata.create_all(bind=engine)

def _ensure_sqlite_columns():
    """Lightweight, safe-in-prod schema guard for SQLite: add missing columns if needed.
    This avoids OperationalError when the ORM model has new columns but existing app.db is older.
    """
    try:
        with engine.connect() as conn:
            # Check existing columns
            info = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
            existing = {row[1] for row in info}  # row[1] is column name

            # Add theme_preference if missing
            if "theme_preference" not in existing:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN theme_preference TEXT DEFAULT 'dark'")

            # Add created_at if missing
            if "created_at" not in existing:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN created_at DATETIME")
    except Exception as e:
        # Don't crash app if migration fails; just log to console
        print("WARN: SQLite column check/migration failed:", e)

# Run schema guard at import time
_ensure_sqlite_columns()

def get_user(email: str):
    # return from the in-memory USERS mapping (used by the template-based login flow)
    return USERS.get(email)

def create_session_cookie(user_email: str):
    return serializer.dumps({"email": user_email})

def parse_session_cookie(cookie_value: str):
    try:
        data = serializer.loads(cookie_value)
        return data
    except Exception:
        return None

async def get_current_user(request: Request):
    cookie = request.cookies.get("session")
    if not cookie:
        return None
    data = parse_session_cookie(cookie)
    if not data:
        return None
    user = get_user(data.get("email"))
    if not user:
        return None
    return {"email": data.get("email"), "name": user["name"], "role": user["role"]}

@app.get("/")
async def index(request: Request, current_user=Depends(get_current_user)):
    # pass current_user into the template so you can show user info
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": current_user,
            "cache_bust": app.state.asset_version,
            "bypass_login": app.state.bypass_login,
            "backend_url": app.state.backend_url
        }
    )

@app.post("/login")
async def template_login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = get_user(username)
    if not user or not auth.verify_password(password, user["password_hash"]):
        # return to login with error or JSON error if XHR
        return templates.TemplateResponse("index.html", {"request": request, "login_error": "Invalid credentials"}, status_code=401)
    # success -> set session cookie and redirect to main app
    resp = RedirectResponse(url="/", status_code=302)
    resp.set_cookie("session", create_session_cookie(username), httponly=True, samesite="lax")
    return resp

@app.get("/logout")
async def logout():
    resp = RedirectResponse(url="/", status_code=302)
    resp.delete_cookie("session")
    return resp

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(auth.get_db)):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        return JSONResponse({"detail":"User exists"}, status_code=400)
    user = models.User(
        email=user_in.email,
        password_hash=auth.get_password_hash(user_in.password),
        name=user_in.name,
        role=user_in.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
@app.post("/api/login")
def api_login(body: dict = Body(...)):
    # debug log to console so you can see what the frontend actually sent
    print("DEBUG /api/login received:", body)

    # accept either 'email' or 'username'
    email = body.get("email") or body.get("username")
    password = body.get("password")
    if not email or not password:
        return JSONResponse({"detail": "Missing credentials (need email/username + password)"}, status_code=400)

    # 1) try DB user (if configured)
    try:
        from db import SessionLocal
        import models
        db = SessionLocal()
        user = db.query(models.User).filter(models.User.email == email).first()
        if user:
            if pwd_ctx.verify(password, getattr(user, "password_hash", "")):
                # Issue a proper JWT so downstream endpoints using OAuth2PasswordBearer work
                token = auth.create_access_token({"sub": email})
                return {"access_token": token, "token_type": "bearer", "user": {"email": user.email, "name": getattr(user, "name", None), "role": getattr(user, "role", None)}}
            else:
                return JSONResponse({"detail": "Invalid credentials (DB)"}, status_code=401)
    except Exception as e:
        # DB not available or error — log it and continue to demo fallback
        print("DEBUG DB error in /api/login:", e)

    # 2) fallback demo users
    DEMO_USERS = {
        "admin@carbontracker.com": {"password": "admin123", "name": "John Admin", "role": "admin"},
        "sarah@steelcorp.com": {"password": "company123", "name": "Sarah Manager", "role": "company"},
        "mike@consulting.com": {"password": "viewer123", "name": "Mike Analyst", "role": "viewer"},
    }
    demo = DEMO_USERS.get(email)
    if demo and demo["password"] == password:
        # Issue JWT for demo users as well so /api/me and other protected routes function
        token = auth.create_access_token({"sub": email})
        return {"access_token": token, "token_type": "bearer", "user": {"email": email, "name": demo["name"], "role": demo["role"]}}

    return JSONResponse({"detail": "Invalid credentials"}, status_code=401)

@app.post("/api/signup")
def api_signup(body: dict = Body(...)):
    """Sign up new user with email and password"""
    print("DEBUG /api/signup received:", body)
    
    email = body.get("email", "").strip()
    password = body.get("password", "")
    name = body.get("name", "").strip()
    
    if not email or not password:
        return JSONResponse({"detail": "Email and password are required"}, status_code=400)
    
    if len(password) < 6:
        return JSONResponse({"detail": "Password must be at least 6 characters long"}, status_code=400)
    
    try:
        from db import SessionLocal
        import models
        db = SessionLocal()
        
        # Check if user already exists
        existing_user = db.query(models.User).filter(models.User.email == email).first()
        if existing_user:
            return JSONResponse({"detail": "User with this email already exists"}, status_code=409)
        
        # Create new user
        password_hash = pwd_ctx.hash(password)
        new_user = models.User(
            email=email,
            password_hash=password_hash,
            name=name or None,
            role="user"  # Default role
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        db.close()
        
        # Generate token for immediate login
        token = f"demo-token:{email}"
        return {
            "access_token": token, 
            "token_type": "bearer", 
            "user": {
                "email": new_user.email, 
                "name": new_user.name, 
                "role": new_user.role
            },
            "message": "Account created successfully!"
        }
        
    except Exception as e:
        print("DEBUG DB error in /api/signup:", e)
        return JSONResponse({"detail": "Failed to create account. Please try again."}, status_code=500)

@app.post("/api/reset-password")
def api_reset_password(body: dict = Body(...)):
    """Reset password for existing user"""
    print("DEBUG /api/reset-password received:", body)
    
    email = body.get("email", "").strip()
    new_password = body.get("new_password", "")
    
    if not email or not new_password:
        return JSONResponse({"detail": "Email and new password are required"}, status_code=400)
    
    if len(new_password) < 6:
        return JSONResponse({"detail": "Password must be at least 6 characters long"}, status_code=400)
    
    try:
        from db import SessionLocal
        import models
        db = SessionLocal()
        
        # Find user
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            return JSONResponse({"detail": "No account found with this email address"}, status_code=404)
        
        # Update password
        user.password_hash = pwd_ctx.hash(new_password)
        db.commit()
        db.close()
        
        return {"message": "Password reset successfully! You can now login with your new password."}
        
    except Exception as e:
        print("DEBUG DB error in /api/reset-password:", e)
        return JSONResponse({"detail": "Failed to reset password. Please try again."}, status_code=500)

@app.get("/api/me", response_model=UserOut)
def me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.post("/api/me/theme")
def update_theme_preference(
    theme: dict = Body(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db)
):
    """Update user's theme preference"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    new_theme = theme.get("theme")
    if new_theme not in ["light", "dark"]:
        raise HTTPException(status_code=400, detail="Theme must be 'light' or 'dark'")
    
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.theme_preference = new_theme
    db.commit()
    db.refresh(user)
    
    return {"theme": user.theme_preference}

@app.post("/api/calculate")
def api_calculate(payload: dict = Body(...)):
    """
    Expects JSON:
    {
      "industry": "steel",
      "production": 1234,         # numeric
      "years": 1,                 # numeric (time period multiplier)
      "energy_source": "coal"     # string
    }
    Returns emissions in tons, credits needed (ceil), and estimated cost.
    """
    industry = payload.get("industry", "") or ""
    try:
        production = float(payload.get("production", 0) or 0)
    except Exception:
        production = 0.0
    try:
        years = float(payload.get("years", 1) or 1)
    except Exception:
        years = 1.0
    energy_source = payload.get("energy_source", "mixed") or "mixed"

    emissions_tons = calculator.calculate_emission(industry, production, years, energy_source)
    credits_needed = math.ceil(emissions_tons)
    # Replace with real price source if available; fallback to 6.97
    credit_price = getattr(app.state, "credit_price", None) or 6.97
    credit_cost = round(credits_needed * float(credit_price), 2)

    return {
        "industry": industry,
        "production": production,
        "years": years,
        "energy_source": energy_source,
        "emissions_tons": emissions_tons,
        "credits_needed": credits_needed,
        "credit_price": credit_price,
        "credit_cost": credit_cost
    }

@app.get("/api/admin/users")
def admin_list_users(db: Session = Depends(auth.get_db), current_user = Depends(auth.get_current_user)):
    """Admin-only: list all users"""
    if not current_user or getattr(current_user, "role", None) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    
    users = db.query(models.User).all()
    return [{"id": u.id, "email": u.email, "name": getattr(u, "name", None), "role": u.role} for u in users]

@app.post("/api/admin/users")
def admin_create_user(payload: dict = Body(...), db: Session = Depends(auth.get_db), current_user = Depends(auth.get_current_user)):
    """Admin-only: create new user with email validation"""
    if not current_user or getattr(current_user, "role", None) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    role = (payload.get("role") or "").strip().lower()
    name = payload.get("name", "").strip()

    # email format validation
    import re
    if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise HTTPException(status_code=400, detail="Valid email address is required")
    
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="Password required (minimum 6 characters)")
    
    if role not in ("company", "viewer"):
        raise HTTPException(status_code=400, detail="Role must be 'company' (manager) or 'viewer' (analyst)")

    # check if user exists
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # create user
    password_hash = auth.get_password_hash(password)
    user = models.User(email=email, password_hash=password_hash, role=role, name=name or None)
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}

@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, db: Session = Depends(auth.get_db), current_user = Depends(auth.get_current_user)):
    """Admin-only: delete user by ID"""
    if not current_user or getattr(current_user, "role", None) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # prevent admin from deleting themselves
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # prevent deleting other admins
    if getattr(user, "role", None) == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin users")

    db.delete(user)
    db.commit()
    return {"message": f"User {user.email} deleted successfully"}

@app.post("/api/ai-predict")
def ai_predict(payload: dict = Body(...)):
    """AI prediction using calculator.py with enhanced forecasting"""
    industry = payload.get("industry", "").lower()
    production = float(payload.get("production", 0) or 0)
    years = float(payload.get("years", 1) or 1)
    energy_source = payload.get("energy_source", "mixed").lower()
    
    # Base calculation using your calculator.py
    base_emissions = calculator.calculate_emission(industry, production, years, energy_source)
    
    # AI-enhanced predictions (simulated with realistic variations)
    confidence = random.uniform(0.75, 0.95)
    
    # Predict next month with seasonal/trend variations
    trend_factor = random.uniform(0.95, 1.08)  # ±8% variation
    next_month_emission = round(base_emissions * trend_factor, 2)
    
    # Determine trend
    if trend_factor > 1.03:
        trend = "increasing"
    elif trend_factor < 0.97:
        trend = "decreasing"
    else:
        trend = "stable"
    
    # Generate AI recommendations based on industry and energy source
    recommendations = generate_ai_recommendations(industry, energy_source, trend_factor)
    
    return {
        "current_emissions": base_emissions,
        "next_month_emission": next_month_emission,
        "confidence": round(confidence, 2),
        "trend": trend,
        "recommendations": recommendations,
        "industry": industry,
        "energy_source": energy_source
    }

def generate_ai_recommendations(industry: str, energy_source: str, trend_factor: float):
    """Generate context-aware recommendations"""
    recommendations = []
    
    # Energy-based recommendations
    if energy_source in ["coal", "oil"]:
        recommendations.append("Switch to renewable energy sources to reduce emissions by 70-90%")
        recommendations.append("Consider hybrid energy systems as an intermediate step")
    elif energy_source == "natural_gas":
        recommendations.append("Upgrade to renewable energy for maximum emission reduction")
    elif energy_source == "mixed":
        recommendations.append("Optimize energy mix by increasing renewable percentage")
    
    # Industry-specific recommendations
    industry_tips = {
        "steel": ["Implement electric arc furnace technology", "Use recycled steel to reduce emissions"],
        "cement": ["Adopt carbon capture and storage (CCS)", "Use alternative fuels in kilns"],
        "textile": ["Implement water recycling systems", "Switch to organic/sustainable materials"],
        "chemical": ["Optimize reaction processes", "Implement heat recovery systems"],
        "other": ["Conduct energy audit", "Implement lean manufacturing processes"]
    }
    
    if industry in industry_tips:
        recommendations.extend(industry_tips[industry])
    
    # Trend-based recommendations
    if trend_factor > 1.05:
        recommendations.append(" Emissions trending upward - immediate action recommended")
        recommendations.append("Review and optimize current processes")
    elif trend_factor < 0.95:
        recommendations.append("Good progress - maintain current efficiency measures")
    
    return recommendations[:5]  # Return top 5 recommendations

@app.get("/api/packaging-materials")
def get_packaging_materials():
    """Return detailed packaging materials data including plastic subtypes"""
    return {
        "plastics": {
            "PET": {"emission_factor": 3.4, "recycled_factor": 1.5, "description": "Polyethylene Terephthalate - bottles, containers"},
            "HDPE": {"emission_factor": 1.9, "recycled_factor": 0.7, "description": "High-Density Polyethylene - milk jugs, detergent bottles"},
            "LDPE": {"emission_factor": 1.8, "recycled_factor": 0.65, "description": "Low-Density Polyethylene - plastic bags, films"},
            "PP": {"emission_factor": 1.95, "recycled_factor": 0.8, "description": "Polypropylene - yogurt containers, caps"},
            "PS": {"emission_factor": 3.1, "recycled_factor": 1.2, "description": "Polystyrene - disposable cups, food containers"},
            "PVC": {"emission_factor": 2.4, "recycled_factor": 1.0, "description": "Polyvinyl Chloride - pipes, packaging films"},
            "Bioplastics": {"emission_factor": 2.1, "recycled_factor": 0.9, "description": "Plant-based plastic alternatives"}
        },
        "paper": {
            "Virgin_Cardboard": {"emission_factor": 0.91, "recycled_factor": 0.73, "description": "New corrugated cardboard"},
            "Recycled_Cardboard": {"emission_factor": 0.73, "recycled_factor": 0.55, "description": "Recycled corrugated cardboard"},
            "Virgin_Paper": {"emission_factor": 1.32, "recycled_factor": 0.95, "description": "Virgin paper packaging"},
            "Recycled_Paper": {"emission_factor": 0.95, "recycled_factor": 0.75, "description": "Recycled paper packaging"}
        },
        "glass": {
            "Clear_Glass": {"emission_factor": 0.85, "recycled_factor": 0.36, "description": "Clear glass containers"},
            "Brown_Glass": {"emission_factor": 0.88, "recycled_factor": 0.37, "description": "Brown glass containers"},
            "Green_Glass": {"emission_factor": 0.87, "recycled_factor": 0.37, "description": "Green glass containers"}
        },
        "metals": {
            "Primary_Aluminum": {"emission_factor": 9.12, "recycled_factor": 0.46, "description": "Virgin aluminum cans and foil"},
            "Recycled_Aluminum": {"emission_factor": 0.46, "recycled_factor": 0.46, "description": "Recycled aluminum packaging"},
            "Steel": {"emission_factor": 1.85, "recycled_factor": 0.36, "description": "Steel cans and containers"}
        },
        "fuels": {
            "Natural_Gas": {"emission_factor": 0.202, "recycled_factor": 0.202, "description": "Natural gas - kg CO₂e per kWh", "unit": "kWh"},
            "Diesel": {"emission_factor": 2.678, "recycled_factor": 2.678, "description": "Diesel fuel - kg CO₂e per liter", "unit": "liter"},
            "Gasoline": {"emission_factor": 2.31, "recycled_factor": 2.31, "description": "Gasoline/petrol - kg CO₂e per liter", "unit": "liter"},
            "Coal": {"emission_factor": 2.23, "recycled_factor": 2.23, "description": "Coal - kg CO₂e per kg", "unit": "kg"},
            "LPG": {"emission_factor": 1.51, "recycled_factor": 1.51, "description": "Liquid Petroleum Gas - kg CO₂e per kg", "unit": "kg"}
        },
        "transportation": {
            "Passenger_Car_Petrol": {"emission_factor": 0.171, "recycled_factor": 0.171, "description": "Petrol car - kg CO₂e per km", "unit": "km"},
            "Passenger_Car_Diesel": {"emission_factor": 0.168, "recycled_factor": 0.168, "description": "Diesel car - kg CO₂e per km", "unit": "km"},
            "Bus": {"emission_factor": 0.089, "recycled_factor": 0.089, "description": "Bus transport - kg CO₂e per km", "unit": "km"},
            "Train": {"emission_factor": 0.041, "recycled_factor": 0.041, "description": "Train transport - kg CO₂e per km", "unit": "km"},
            "Domestic_Flight": {"emission_factor": 0.255, "recycled_factor": 0.255, "description": "Domestic flight - kg CO₂e per km", "unit": "km"},
            "International_Flight": {"emission_factor": 0.195, "recycled_factor": 0.195, "description": "International flight - kg CO₂e per km", "unit": "km"}
        },
        "waste": {
            "Landfill": {"emission_factor": 0.525, "recycled_factor": 0.525, "description": "Landfill waste - kg CO₂e per kg", "unit": "kg"},
            "Recycling": {"emission_factor": 0.021, "recycled_factor": 0.021, "description": "Recycled waste - kg CO₂e per kg", "unit": "kg"},
            "Incineration": {"emission_factor": 0.025, "recycled_factor": 0.025, "description": "Incinerated waste - kg CO₂e per kg", "unit": "kg"}
        },
        "carbon_credit_price": 6.5
    }

@app.post("/api/calculate-packaging")
def calculate_packaging_emissions(payload: dict = Body(...)):
    """Calculate emissions for packaging materials"""
    # Extract payload data
    material_type = payload.get("material_type", "").lower()
    material_subtype = payload.get("material_subtype", "")
    amount = float(payload.get("amount", 0) or 0)
    state = payload.get("state", "solid").lower()
    is_recycled = payload.get("is_recycled", False)
    transport_distance = float(payload.get("transport_distance", 0) or 0)
    transport_mode = payload.get("transport_mode", "truck").lower()
    unit = payload.get("unit", "kg")
    
    # Get materials data
    materials = get_packaging_materials()
    
    # Get emission factor
    emission_factor = 0
    if material_type in materials and material_subtype in materials[material_type]:
        if is_recycled and material_type not in ["fuels", "transportation", "waste"]:
            emission_factor = materials[material_type][material_subtype]["recycled_factor"]
        else:
            emission_factor = materials[material_type][material_subtype]["emission_factor"]
    
    # Calculate base emissions
    base_emissions = amount * emission_factor
    
    # Transport emissions (simplified calculation)
    transport_factors = {
        "truck": 0.12, 
        "ship": 0.014, 
        "air": 0.5, 
        "rail": 0.04
    }
    transport_factor = transport_factors.get(transport_mode, 0.1)
    transport_emissions = amount * transport_factor * transport_distance / 1000 if transport_distance > 0 else 0
    
    # Total emissions
    total_emissions = base_emissions + transport_emissions
    
    # Calculate credits needed (1 credit per tonne CO2e, minimum 1)
    credits_needed = max(1, math.ceil(total_emissions / 1000))
    
    # Calculate cost
    credit_price = materials.get("carbon_credit_price", 6.5)
    credit_cost = credits_needed * credit_price
    
    # Generate appropriate recommendations based on material type
    recommendations = []
    
    if material_type == "plastics":
        if not is_recycled:
            recycled_emissions = amount * materials[material_type][material_subtype]["recycled_factor"]
            savings = base_emissions - recycled_emissions
            recommendations.append(f"Switch to recycled {material_subtype} to save {round(savings, 2)} kg CO₂e")
        recommendations.append("Consider lighter packaging design to reduce material usage")
        recommendations.append("Implement a packaging return program for reuse")
    
    elif material_type == "fuels":
        if material_subtype in ["Natural_Gas", "Diesel", "Gasoline", "Coal"]:
            recommendations.append("Consider renewable energy alternatives")
            recommendations.append("Improve energy efficiency to reduce consumption")
            if material_subtype == "Coal":
                recommendations.append("Switch to cleaner fuels like natural gas for a 60% emission reduction")
            elif material_subtype in ["Diesel", "Gasoline"]:
                recommendations.append("Consider electric vehicles to reduce fuel emissions")
    
    elif material_type == "transportation":
        if material_subtype in ["Passenger_Car_Petrol", "Passenger_Car_Diesel"]:
            recommendations.append("Consider carpooling to reduce per-person emissions")
            recommendations.append("Use public transportation when possible")
        elif material_subtype in ["Domestic_Flight", "International_Flight"]:
            train_emission = 0.041 * amount  # Using the train emission factor
            flight_saving = base_emissions - train_emission
            recommendations.append(f"Consider train travel instead to save {round(flight_saving, 2)} kg CO₂e")
        recommendations.append("Optimize route planning to minimize distance traveled")
    
    elif material_type == "waste":
        if material_subtype == "Landfill":
            recycle_emission = materials["waste"]["Recycling"]["emission_factor"] * amount
            waste_saving = base_emissions - recycle_emission
            recommendations.append(f"Switch to recycling to save {round(waste_saving, 2)} kg CO₂e")
            recommendations.append("Implement waste reduction strategies")
        recommendations.append("Consider composting for organic waste")
    
    else:
        # General recommendations for other material types
        if transport_mode == "air":
            ship_emissions = amount * 0.014 * transport_distance / 1000
            savings = transport_emissions - ship_emissions
            recommendations.append(f"Switch from air to sea freight to save {round(savings, 2)} kg CO₂e")
    
        # Find alternative with lower emissions in same category
        if material_type in materials:
            current = emission_factor
            alternatives = []
            for subtype, data in materials[material_type].items():
                if subtype != material_subtype:
                    factor = data["recycled_factor"] if is_recycled else data["emission_factor"]
                    if factor < current:
                        alternatives.append((subtype, factor, data["description"]))
            
            if alternatives:
                best = min(alternatives, key=lambda x: x[1])
                potential_savings = amount * (current - best[1])
                recommendations.append(f"Consider {best[0].replace('_', ' ')} ({best[2].split(' - ')[0]}) to save {round(potential_savings, 2)} kg CO₂e")
    
    # Add more recommendations if we don't have enough
    if len(recommendations) < 3:
        recommendations.append("Consider carbon offsetting programs for unavoidable emissions")
        recommendations.append("Track and report emissions to identify future reduction opportunities")
    
    return {
        "material_type": material_type,
        "material_subtype": material_subtype,
        "amount": amount,
        "state": state,
        "is_recycled": is_recycled,
        "transport": {
            "mode": transport_mode,
            "distance": transport_distance,
            "emissions": round(transport_emissions, 2)
        },
        "material_emissions": round(base_emissions, 2),
        "total_emissions": round(total_emissions, 2),
        "credits_needed": credits_needed,
        "credit_price": credit_price,
        "credit_cost": round(credit_cost, 2),
        "recommendations": recommendations[:3]  # Top 3 recommendations
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
