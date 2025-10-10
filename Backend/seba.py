from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form, Response, Depends
from fastapi.middleware.cors import CORSMiddleware #nueva importación
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm # Necesario para el flujo de login estándar de FastAPI
from pathlib import Path
from pydantic import BaseModel, field_validator
from typing import Optional, List, Generator
from datetime import datetime, timedelta, timezone, date
import uuid
from passlib.context import CryptContext
from jose import jwt, JWTError
import re
from enum import Enum



from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    Boolean,
    select,
    func,
    Date,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session


app = FastAPI(title="Strategic Plan API (DB-backed)")

# ---- Configuración de CORS ----

origins = [
    "http://127.0.0.1",  # Dirección común para el localhost
    "http://localhost",
    "*", # <-- Permite cualquier origen (solo para desarrollo)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Lista de orígenes permitidos
    allow_credentials=True,         # Permitir cookies y encabezados de autenticación
    allow_methods=["*"],            # Permitir todos los métodos (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],            # Permitir todos los encabezados
)
# -----------------------------

# ---- Config ----
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---- Configuración de Seguridad ----

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "COLEGIO_ARZOBISPADO" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ------- Database URL (MySQL) --------
DATABASE_URL = "mysql+pymysql://root:2025@127.0.0.1:3306/colegio_db"

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# ------------------------codigo nuevo---------------------

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

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserModel:
    """Decodifica el token, maneja la expiración/invalidez (401) y retorna el usuario."""
    
    # Excepción estándar 401
    credentials_exception = HTTPException(
        status_code=401,
        detail="Credenciales inválidas (token ausente o expirado)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodifica el token usando SECRET_KEY y ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Lee la clave estándar "sub" (subject)
        username: str = payload.get("sub") 
        
        if username is None:
            raise credentials_exception
            
    except JWTError:
        # Si la decodificación falla (token expirado, firma incorrecta, etc.)
        raise credentials_exception
    
    # Busca el usuario por el nombre de usuario ('sub')
    user = db.execute(
        select(UserModel).where(UserModel.name == username)).scalar_one_or_none()
    
    if user is None:
        raise credentials_exception # Usuario no encontrado, 401
        
    # Puedes añadir la verificación de actividad de la Versión 1 si es necesaria
    if not user.is_active: 
        raise credentials_exception

    return user

def require_role(*roles: str):
    """
    Dependencia de seguridad que verifica si el usuario autenticado
    (obtenido de get_current_user) tiene uno de los roles especificados.
    Lanza 403 Forbidden si no tiene el rol.
    """
    def _dep(user: UserModel = Depends(get_current_user)) -> UserModel:
        # user.role es la columna de rol en tu modelo SQLAlchemy
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return user
    return _dep


# ==============================
# Utilidades & validaciones
# ==============================
def _dv_mod11(num: str) -> str:
    serie = [2,3,4,5,6,7]
    s, i = 0, 0
    for d in reversed(num):
        s += int(d) * serie[i % len(serie)]
        i += 1
    resto = 11 - (s % 11)
    if resto == 11: return "0"
    if resto == 10: return "K"
    return str(resto)

def normalize_rut(rut: str) -> str:
    s = re.sub(r"[^0-9kK]", "", rut or "")
    if len(s) < 2:
        raise HTTPException(status_code=400, detail="RUT inválido")
    cuerpo, dv = s[:-1], s[-1].upper()
    if not cuerpo.isdigit():
        raise HTTPException(status_code=400, detail="RUT inválido")
    if _dv_mod11(cuerpo) != dv:
        # usamos mismo mensaje para no filtrar info
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    # PRESERVA CEROS A LA IZQUIERDA
    return cuerpo + dv

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


# ---- Schemas ----

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


class DimensionEnum(str, Enum):
    LIDERAZGO = "LIDERAZGO"
    GESTION_PEDAGOGICA = "GESTION_PEDAGOGICA"
    CONVIVENCIA_ESCOLAR = "CONVIVENCIA_ESCOLAR"
    GESTION_RECURSOS = "GESTION_RECURSOS"

class RoleEnum(str, Enum):
    editor = "editor"
    viewer = "viewer"

class StrategicPlanCreate(BaseModel):
    dimension: DimensionEnum
    colegio: str                          # nombre del colegio (v1 simple; luego puedes hacer catálogo)
    objetivo_estrategico: str
    estrategia: str
    subdimension: Optional[str] = None
    accion: str
    descripcion: Optional[str] = None
    fecha_inicio: date
    fecha_termino: date
    programa_asociado: Optional[str] = None
    responsable: str

    @field_validator("fecha_termino")
    @classmethod
    def _fin_despues_de_inicio(cls, v: date, info):
        ini = info.data.get("fecha_inicio")
        if ini and v < ini:
            raise ValueError("La Fecha Término debe ser mayor o igual a la Fecha Inicio")
        return v


class StrategicResourceCreate(BaseModel):
    recursos_necesarios: Optional[str] = None
    ate: Optional[str] = None
    tic: Optional[str] = None
    planes: Optional[str] = None
    medios_verificacion: Optional[str] = None
    monto_subvencion_general: Optional[int] = 0
    monto_sep: Optional[int] = 0
    monto_pie: Optional[int] = 0
    monto_eib: Optional[int] = 0
    monto_mantenimiento: Optional[int] = 0
    monto_pro_retencion: Optional[int] = 0
    monto_internado: Optional[int] = 0
    monto_reforzamiento: Optional[int] = 0
    monto_faep: Optional[int] = 0
    monto_aporte_municipal: Optional[int] = 0
    monto_total: Optional[int] = 0


class StrategicResource(StrategicResourceCreate):
    id: int
    plan_id: int


class StrategicPlan(StrategicPlanCreate):
    id: int
    created_at: datetime


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel): 
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel): 
    sub: Optional[str] = None 
    role: Optional[str] = None


class MeOut(BaseModel):
    id: int
    rut: str
    name: str
    email: str
    role: str
    is_active: bool

@app.get("/auth/me", response_model=MeOut)
def me(u: UserModel = Depends(get_current_user)):
    return MeOut(id=u.id, rut=u.rut, name=u.name, email=u.email, role=u.role, is_active=u.is_active)

# ---- ORM Models ----

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
    rut = Column(String(12), unique=True, nullable=False, index=True) 
    name = Column(String(190), unique=True, nullable=False, index=True) 
    email = Column(String(190), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False) 
    is_active = Column(Boolean, nullable=False, server_default="1")
    role = Column(String(20), nullable=False, server_default="viewer")
    created_at = Column(DateTime, server_default=func.current_timestamp())

class StrategicPlanModel(Base):
    __tablename__ = "strategic_plans"
    id = Column(Integer, primary_key=True, index=True)

    dimension = Column(String(40), nullable=False, index=True)

    colegio = Column(String(200), nullable=False)
    objetivo_estrategico = Column(Text, nullable=False)
    estrategia = Column(Text, nullable=False)
    subdimension = Column(String(120), nullable=True)
    accion = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)

    fecha_inicio = Column(Date, nullable=False)
    fecha_termino = Column(Date, nullable=False)

    programa_asociado = Column(String(255), nullable=True)
    responsable = Column(String(120), nullable=False)

    created_at = Column(DateTime, server_default=func.current_timestamp())
    resources = relationship(
        "StrategicResourceModel",
        back_populates="plan",
        cascade="all, delete-orphan"
    )
#recursos
class StrategicResourceModel(Base):
    __tablename__ = "plan_resources"

    id   = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("strategic_plans.id", ondelete="CASCADE"),
                     nullable=False, index=True)

    # campos “texto”
    recursos_necesarios   = Column(Text, nullable=True)
    ate                   = Column(String(120), nullable=True)
    tic                   = Column(String(120), nullable=True)
    planes                = Column(String(255), nullable=True)
    medios_verificacion   = Column(Text, nullable=True)

    # montos (elige Integer si no usarás decimales)
    monto_subvencion_general = Column(Integer, nullable=True, default=0)
    monto_sep                = Column(Integer, nullable=True, default=0)
    monto_pie                = Column(Integer, nullable=True, default=0)
    monto_eib                = Column(Integer, nullable=True, default=0)
    monto_mantenimiento      = Column(Integer, nullable=True, default=0)
    monto_pro_retencion      = Column(Integer, nullable=True, default=0)
    monto_internado          = Column(Integer, nullable=True, default=0)
    monto_reforzamiento      = Column(Integer, nullable=True, default=0)
    monto_faep               = Column(Integer, nullable=True, default=0)
    monto_aporte_municipal   = Column(Integer, nullable=True, default=0)
    monto_total              = Column(Integer, nullable=True, default=0)

    plan = relationship("StrategicPlanModel", back_populates="resources")


# ---- Converters (ORM -> Pydantic) ----

def objective_to_pydantic(m: ObjectiveModel) -> Objective:
    return Objective(
        id=m.id,
        name=m.name,
        description=m.description,
        start_year=m.start_year,
        end_year=m.end_year,
    )


def goal_to_pydantic(m: GoalModel) -> Goal:
    return Goal(
        id=m.id,
        objective_id=m.objective_id,
        title=m.title,
        description=m.description,
        year=m.year,
    )


def indicator_to_pydantic(m: IndicatorModel) -> Indicator:
    return Indicator(
        id=m.id,
        goal_id=m.goal_id,
        title=m.title,
        target=m.target,
        unit=m.unit,
    )


def evidence_to_pydantic(m: EvidenceModel) -> Evidence:
    return Evidence(
        id=m.id,
        indicator_id=m.indicator_id,
        description=m.description or "",
        filename=m.filename,
        original_filename=m.original_filename,
        uploaded_at=m.uploaded_at,
    )


def plan_to_pydantic(m: StrategicPlanModel) -> StrategicPlan:
    return StrategicPlan(
        id=m.id,
        dimension=m.dimension,
        colegio=m.colegio,
        objetivo_estrategico=m.objetivo_estrategico,
        estrategia=m.estrategia,
        subdimension=m.subdimension,
        accion=m.accion,
        descripcion=m.descripcion,
        fecha_inicio=m.fecha_inicio,
        fecha_termino=m.fecha_termino,
        programa_asociado=m.programa_asociado,
        responsable=m.responsable,
        created_at=m.created_at,
    )


def Resource_to_pydantic(m: StrategicResourceModel) -> StrategicResource:
    return StrategicResource(
        id=m.id,
        plan_id=m.plan_id,
        recursos_necesarios=m.recursos_necesarios,
        ate=m.ate,
        tic=m.tic,
        planes=m.planes,
        medios_verificacion=m.medios_verificacion,
        monto_subvencion_general=m.monto_subvencion_general,
        monto_sep=m.monto_sep,
        monto_pie=m.monto_pie,
        monto_eib=m.monto_eib,
        monto_mantenimiento=m.monto_mantenimiento,
        monto_pro_retencion=m.monto_pro_retencion,
        monto_internado=m.monto_internado,
        monto_reforzamiento=m.monto_reforzamiento,
        monto_faep=m.monto_faep,
        monto_aporte_municipal=m.monto_aporte_municipal,
        monto_total=m.monto_total,
    )


# ---- Helpers de Seguridad (Añadir en cualquier lugar antes de las rutas) ----

def hash_password(password: str) -> str:
    """Hashea una contraseña para almacenarla."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, password: str) -> bool:
    """Verifica una contraseña contra un hash."""
    return pwd_context.verify(plain_password, password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Genera un token de acceso JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ---- Routes ----

# Objectives
@app.post("/objectives", response_model=Objective, status_code=201)
def create_objective(payload: ObjectiveCreate, db: Session = Depends(get_db)):
    m = ObjectiveModel(**asdict(payload))
    db.add(m)
    db.flush()
    return objective_to_pydantic(m)


@app.get("/objectives", response_model=List[Objective])
def list_objectives(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
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
    # Validate parent + year-in-range
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
def list_goals(
    objective_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = (
        select(GoalModel)
        .where(GoalModel.objective_id == objective_id)
        .order_by(GoalModel.id)
        .offset(skip)
        .limit(limit)
    )
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
def list_indicators(
    goal_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = (
        select(IndicatorModel)
        .where(IndicatorModel.goal_id == goal_id)
        .order_by(IndicatorModel.id)
        .offset(skip)
        .limit(limit)
    )
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


# Evidences
@app.post("/indicators/{indicator_id}/evidences", response_model=Evidence, status_code=201)
def upload_evidence(
    indicator_id: int,
    file: UploadFile = File(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
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

    m = EvidenceModel(
        indicator_id=indicator_id,
        description=description,
        filename=filename,
        original_filename=file.filename,
        uploaded_at=datetime.utcnow(),
    )
    db.add(m)
    db.flush()
    return evidence_to_pydantic(m)


@app.get("/indicators/{indicator_id}/evidences", response_model=List[Evidence])
def list_evidences(
    indicator_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if not db.get(IndicatorModel, indicator_id):
        raise HTTPException(status_code=404, detail="Indicator not found")
    stmt = (
        select(EvidenceModel)
        .where(EvidenceModel.indicator_id == indicator_id)
        .order_by(EvidenceModel.id)
        .offset(skip)
        .limit(limit)
    )
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

#login
@app.post("/auth/login", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """Endpoint para autenticar al usuario y generar un token JWT."""
    user = db.execute(select(UserModel).where(UserModel.name == form_data.username)).scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=400,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    token_payload = {
        "sub": user.name,
        "role": user.role
    }

    access_token = create_access_token(
        token_payload, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


# ==============================
# Strategic Plans API
# ==============================
# Crear plan (solo editor)
@app.post("/plans", response_model=StrategicPlan, status_code=201)
def create_plan(
    payload: StrategicPlanCreate, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role("editor")), # <- aquí
):
    m = StrategicPlanModel(
        dimension=payload.dimension.value,
        colegio=payload.colegio,
        objetivo_estrategico=payload.objetivo_estrategico,
        estrategia=payload.estrategia,
        subdimension=payload.subdimension,
        accion=payload.accion,
        descripcion=payload.descripcion,
        fecha_inicio=payload.fecha_inicio,
        fecha_termino=payload.fecha_termino,
        programa_asociado=payload.programa_asociado,
        responsable=payload.responsable,
    )
    db.add(m)
    db.flush()
    return plan_to_pydantic(m)

@app.get("/plans", response_model=List[StrategicPlan])
def list_plans(
    dimension: Optional[DimensionEnum] = Query(None),
    colegio: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    # si quieres requerir login incluso para ver, descomenta:
    # _: UserModel = Depends(get_current_user),
):
    stmt = select(StrategicPlanModel).order_by(StrategicPlanModel.id)
    if dimension:
        stmt = stmt.where(StrategicPlanModel.dimension == dimension.value)
    if colegio:
        stmt = stmt.where(StrategicPlanModel.colegio == colegio)
    rows = db.execute(stmt.offset(skip).limit(limit)).scalars().all()
    return [plan_to_pydantic(r) for r in rows]

# Catálogo de dimensiones (solo lectura)
@app.get("/plans/dimensions", response_model=List[str])
def list_dimensions():
    return [d.value for d in DimensionEnum]

# Obtener un plan (solo lectura)
@app.get("/plans/{plan_id}", response_model=StrategicPlan)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    m = db.get(StrategicPlanModel, plan_id)
    if not m:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    return plan_to_pydantic(m)

# Eliminar plan (solo editor)
@app.delete("/plans/{plan_id}", status_code=204)
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role("editor")),  # <- aquí
):
    m = db.get(StrategicPlanModel, plan_id)
    if not m:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    db.delete(m)
    return Response(status_code=204)

# Crear recursos (solo editor)
@app.post("/plans/{plan_id}/resources", response_model=StrategicResource, status_code=201)
def create_resource(
    plan_id: int,
    payload: StrategicResourceCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role("editor")),  # <- aquí
):
    plan = db.get(StrategicPlanModel, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    # Calcula total si no viene
    if not payload.monto_total:
        nums = [
            payload.monto_subvencion_general or 0,
            payload.monto_sep or 0,
            payload.monto_pie or 0,
            payload.monto_eib or 0,
            payload.monto_mantenimiento or 0,
            payload.monto_pro_retencion or 0,
            payload.monto_internado or 0,
            payload.monto_reforzamiento or 0,
            payload.monto_faep or 0,
            payload.monto_aporte_municipal or 0,
        ]
        payload.monto_total = sum(nums)

    m = StrategicResourceModel(plan_id=plan_id, **asdict(payload))
    db.add(m)
    db.flush()
    return Resource_to_pydantic(m)


# Listar recursos de un plan (lectura)
@app.get("/plans/{plan_id}/resources", response_model=List[StrategicResource])
def list_resources(plan_id: int, db: Session = Depends(get_db)):
    rows = db.execute(select(StrategicResourceModel).where(StrategicResourceModel.plan_id==plan_id)).scalars().all()
    return [Resource_to_pydantic(r) for r in rows]

# Eliminar recurso (solo editor)
@app.delete("/resources/{resource_id}", status_code=204)
def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role("editor")),  # <- aquí
):
    m = db.get(StrategicResourceModel, resource_id)
    if not m:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    db.delete(m)
    return Response(status_code=204)

# Health
@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    # Ensure upload dir exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
