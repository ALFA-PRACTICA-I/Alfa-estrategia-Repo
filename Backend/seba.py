#python -m uvicorn backend.seba:app --reload
from __future__ import annotations

# --- FastAPI & core ---
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Optional, List, Generator
from datetime import datetime, timedelta
import uuid
from sqlalchemy import Boolean
from sqlalchemy import select
# --- Pydantic ---
from pydantic import BaseModel, field_validator

# --- SQLAlchemy ---
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, select, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

# --- Auth (password & JWT) ---
from passlib.context import CryptContext
from jose import JWTError, jwt
from contextlib import asynccontextmanager



# ==============================
# Configuración general
# ==============================


SECRET_KEY = "hola123"   # en prod usa variable de entorno
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
#pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
#print(pwd.hash("hola123"))

def verify_password(plain: str, password_hash: str) -> bool:
    return pwd_context.verify(plain, password_hash)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(minutes=minutes)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


Base = declarative_base()

app = FastAPI(title="Strategic Plan API (DB-backed)")

# Habilita CORS para poder llamar desde tu HTML/JS local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # en prod, pon el origen exacto (ej. http://127.0.0.1:5500)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---- Config ----
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---- Config DB ----
# Cambia la clave 'ruta' por tu contraseña real, o usa un usuario distinto a root
DATABASE_URL = "mysql+pymysql://root:ruta@localhost:3306/colegio_db"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# ==============================
# Utilidades & validaciones
# ==============================

def asdict(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()

CURRENT_YEAR = datetime.utcnow().year
MIN_YEAR = 1900
MAX_YEAR = CURRENT_YEAR + 10

ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".docx"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
COPY_CHUNK_SIZE = 1024 * 1024        # 1 MB

# ==============================
# Schemas (Pydantic)
# ==============================

class ObjectiveCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_year: int
    end_year: int

    @field_validator("start_year", "end_year")
    @classmethod
    def _reasonable_year(cls, v: int):
        if v < MIN_YEAR or v > MAX_YEAR:
            raise ValueError(f"year must be between {MIN_YEAR} and {MAX_YEAR}")
        return v

    @field_validator("end_year")
    @classmethod
    def _end_after_start(cls, v: int, info):
        start = info.data.get("start_year")
        if start is not None and v < start:
            raise ValueError("end_year must be >= start_year")
        return v

class Objective(ObjectiveCreate):
    id: int

class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    year: int

    @field_validator("year")
    @classmethod
    def _reasonable_year(cls, v: int):
        if v < MIN_YEAR or v > MAX_YEAR:
            raise ValueError(f"year must be between {MIN_YEAR} and {MAX_YEAR}")
        return v

class Goal(GoalCreate):
    id: int
    objective_id: int

class IndicatorCreate(BaseModel):
    title: str
    target: Optional[str] = None
    unit: Optional[str] = None

class Indicator(IndicatorCreate):
    id: int
    goal_id: int

class EvidenceCreate(BaseModel):
    description: Optional[str] = ""
    filename: str
    original_filename: Optional[str] = None

class Evidence(EvidenceCreate):
    id: int
    indicator_id: int
    uploaded_at: datetime

# --- Login schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ==============================
# Modelos ORM (tablas)
# ==============================

class ObjectiveModel(Base):
    __tablename__ = "objectives"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=False)
    goals = relationship("GoalModel", back_populates="objective")

class GoalModel(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    year = Column(Integer, nullable=False)
    objective_id = Column(Integer, ForeignKey("objectives.id", ondelete="RESTRICT"), nullable=False, index=True)
    objective = relationship("ObjectiveModel", back_populates="goals")
    indicators = relationship("IndicatorModel", back_populates="goal")

class IndicatorModel(Base):
    __tablename__ = "indicators"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    target = Column(Text, nullable=True)
    unit = Column(String(50), nullable=True)
    goal_id = Column(Integer, ForeignKey("goals.id", ondelete="RESTRICT"), nullable=False, index=True)
    goal = relationship("GoalModel", back_populates="indicators")
    evidences = relationship("EvidenceModel", back_populates="indicator")

class EvidenceModel(Base):
    __tablename__ = "evidences"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    indicator_id = Column(Integer, ForeignKey("indicators.id", ondelete="RESTRICT"), nullable=False, index=True)
    indicator = relationship("IndicatorModel", back_populates="evidences")

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(190), unique=True, nullable=False, index=True)  # <- antes username
    email = Column(String(190), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)                      # <- antes password_hash
    is_active = Column(Boolean, nullable=False, server_default="1")
    created_at = Column(DateTime, server_default=func.current_timestamp())

# ==============================
# DB dependency (una sesión por request)
# ==============================

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# ==============================
# Converters ORM -> Pydantic
# ==============================

def objective_to_pydantic(m: ObjectiveModel) -> Objective:
    return Objective(id=m.id, name=m.name, description=m.description, start_year=m.start_year, end_year=m.end_year)

def goal_to_pydantic(m: GoalModel) -> Goal:
    return Goal(id=m.id, objective_id=m.objective_id, title=m.title, description=m.description, year=m.year)

def indicator_to_pydantic(m: IndicatorModel) -> Indicator:
    return Indicator(id=m.id, goal_id=m.goal_id, title=m.title, target=m.target, unit=m.unit)

def evidence_to_pydantic(m: EvidenceModel) -> Evidence:
    return Evidence(id=m.id, indicator_id=m.indicator_id, description=m.description or "", filename=m.filename,
                    original_filename=m.original_filename, uploaded_at=m.uploaded_at)

# ==============================
# Rutas de negocio
# ==============================

# Objectives
@app.post("/objectives", response_model=Objective, status_code=201)
def create_objective(payload: ObjectiveCreate, db: Session = Depends(get_db)):
    m = ObjectiveModel(**asdict(payload))
    db.add(m)
    db.flush()
    return objective_to_pydantic(m)

@app.get("/objectives", response_model=List[Objective])
def list_objectives(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    stmt = select(ObjectiveModel).order_by(ObjectiveModel.id).offset(skip).limit(limit)
    objs = db.execute(stmt).scalars().all()
    return [objective_to_pydantic(o) for o in objs]

@app.get("/objectives/{objective_id}", response_model=Objective)
def get_objective(objective_id: int, db: Session = Depends(get_db)):
    m = db.get(ObjectiveModel, objective_id)
    if not m:
        raise HTTPException(status_code=404, detail="Objective not found")
    return objective_to_pydantic(m)

@app.delete("/objectives/{objective_id}", status_code=204)
def delete_objective(objective_id: int, db: Session = Depends(get_db)):
    m = db.get(ObjectiveModel, objective_id)
    if not m:
        raise HTTPException(status_code=404, detail="Objective not found")
    child_count = db.execute(select(func.count(GoalModel.id)).where(GoalModel.objective_id == objective_id)).scalar()
    if child_count and child_count > 0:
        raise HTTPException(status_code=409, detail="Objective has goals; delete them first")
    db.delete(m)
    return Response(status_code=204)

# Goals
@app.post("/objectives/{objective_id}/goals", response_model=Goal, status_code=201)
def create_goal(objective_id: int, payload: GoalCreate, db: Session = Depends(get_db)):
    obj = db.get(ObjectiveModel, objective_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
    if not (obj.start_year <= payload.year <= obj.end_year):
        raise HTTPException(status_code=400, detail="Goal year must be within the objective period")
    m = GoalModel(objective_id=objective_id, **asdict(payload))
    db.add(m)
    db.flush()
    return goal_to_pydantic(m)

@app.get("/objectives/{objective_id}/goals", response_model=List[Goal])
def list_goals(objective_id: int, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    stmt = select(GoalModel).where(GoalModel.objective_id == objective_id).order_by(GoalModel.id).offset(skip).limit(limit)
    goals = db.execute(stmt).scalars().all()
    return [goal_to_pydantic(g) for g in goals]

@app.get("/goals/{goal_id}", response_model=Goal)
def get_goal(goal_id: int, db: Session = Depends(get_db)):
    m = db.get(GoalModel, goal_id)
    if not m:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal_to_pydantic(m)

@app.delete("/goals/{goal_id}", status_code=204)
def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    m = db.get(GoalModel, goal_id)
    if not m:
        raise HTTPException(status_code=404, detail="Goal not found")
    child_count = db.execute(select(func.count(IndicatorModel.id)).where(IndicatorModel.goal_id == goal_id)).scalar()
    if child_count and child_count > 0:
        raise HTTPException(status_code=409, detail="Goal has indicators; delete them first")
    db.delete(m)
    return Response(status_code=204)

# Indicators
@app.post("/goals/{goal_id}/indicators", response_model=Indicator, status_code=201)
def create_indicator(goal_id: int, payload: IndicatorCreate, db: Session = Depends(get_db)):
    parent = db.get(GoalModel, goal_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Goal not found")
    m = IndicatorModel(goal_id=goal_id, **asdict(payload))
    db.add(m)
    db.flush()
    return indicator_to_pydantic(m)

@app.get("/goals/{goal_id}/indicators", response_model=List[Indicator])
def list_indicators(goal_id: int, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    stmt = select(IndicatorModel).where(IndicatorModel.goal_id == goal_id).order_by(IndicatorModel.id).offset(skip).limit(limit)
    inds = db.execute(stmt).scalars().all()
    return [indicator_to_pydantic(i) for i in inds]

@app.get("/indicators/{indicator_id}", response_model=Indicator)
def get_indicator(indicator_id: int, db: Session = Depends(get_db)):
    m = db.get(IndicatorModel, indicator_id)
    if not m:
        raise HTTPException(status_code=404, detail="Indicator not found")
    return indicator_to_pydantic(m)

@app.delete("/indicators/{indicator_id}", status_code=204)
def delete_indicator(indicator_id: int, db: Session = Depends(get_db)):
    m = db.get(IndicatorModel, indicator_id)
    if not m:
        raise HTTPException(status_code=404, detail="Indicator not found")
    child_count = db.execute(select(func.count(EvidenceModel.id)).where(EvidenceModel.indicator_id == indicator_id)).scalar()
    if child_count and child_count > 0:
        raise HTTPException(status_code=409, detail="Indicator has evidences; delete them first")
    db.delete(m)
    return Response(status_code=204)

# Evidences (upload)
@app.post("/indicators/{indicator_id}/evidences", response_model=Evidence, status_code=201)
def upload_evidence(indicator_id: int, file: UploadFile = File(...), description: str = Form(""), db: Session = Depends(get_db)):
    ind = db.get(IndicatorModel, indicator_id)
    if not ind:
        raise HTTPException(status_code=404, detail="Indicator not found")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=415, detail=f"Unsupported file type '{ext}'")
    filename = f"{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / filename
    bytes_written = 0
    with dest.open("wb") as buffer:
        while True:
            chunk = file.file.read(COPY_CHUNK_SIZE)
            if not chunk:
                break
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_BYTES:
                buffer.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File too large")
            buffer.write(chunk)
    m = EvidenceModel(indicator_id=indicator_id, description=description, filename=filename,
                      original_filename=file.filename, uploaded_at=datetime.utcnow())
    db.add(m)
    db.flush()
    return evidence_to_pydantic(m)

@app.get("/indicators/{indicator_id}/evidences", response_model=List[Evidence])
def list_evidences(indicator_id: int, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    if not db.get(IndicatorModel, indicator_id):
        raise HTTPException(status_code=404, detail="Indicator not found")
    stmt = select(EvidenceModel).where(EvidenceModel.indicator_id == indicator_id).order_by(EvidenceModel.id).offset(skip).limit(limit)
    evs = db.execute(stmt).scalars().all()
    return [evidence_to_pydantic(e) for e in evs]

@app.get("/evidences/{evidence_id}", response_model=Evidence)
def get_evidence(evidence_id: int, db: Session = Depends(get_db)):
    m = db.get(EvidenceModel, evidence_id)
    if not m:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence_to_pydantic(m)

@app.delete("/evidences/{evidence_id}", status_code=204)
def delete_evidence(evidence_id: int, db: Session = Depends(get_db)):
    m = db.get(EvidenceModel, evidence_id)
    if not m:
        raise HTTPException(status_code=404, detail="Evidence not found")
    filename = m.filename
    db.delete(m)
    try:
        (UPLOAD_DIR / filename).unlink(missing_ok=True)
    except Exception:
        pass
    return Response(status_code=204)

from sqlalchemy import select

@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(
        select(UserModel).where(UserModel.name == payload.username)
    ).scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # La contraseña en DB DEBE ser un hash bcrypt
    if not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # El 'id' no se escribe en el login; aquí solo lo metemos en el token por conveniencia (puedes quitarlo)
    token = create_access_token({"sub": user.name, "uid": user.id})
    return TokenResponse(access_token=token)

# ==============================
# Health & startup
# ==============================

@app.get("/")
def health():
    return {"status": "ok"}




    