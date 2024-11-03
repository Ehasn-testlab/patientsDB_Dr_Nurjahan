from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, EmailStr
from typing import List
from datetime import date
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import relationship

# Database connection setup
DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/patient_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Patient ORM Model
class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    phone = Column(String(15), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    address = Column(String(255), nullable=True)
    age = Column(Integer)
    medical_records = relationship("MedicalRecord", back_populates="patient")

class MedicalRecord(Base):
    __tablename__ = "medical_records"

    record_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    diagnosis = Column(Text)
    treatment = Column(Text)
    prescription = Column(Text)
    notes = Column(Text)
    record_date = Column(Date)
    patient = relationship("Patient", back_populates="medical_records") 




# Pydantic models for request and response validation
class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    phone: str
    email: EmailStr
    address: str
    age: int
    medical_records: List[MedicalRecord] = []

class MedicalRecord(BaseModel):
    record_id: Optional[int]
    patient_id: int
    diagnosis: str
    treatment: str
    prescription: str
    notes: Optional[str] = None
    record_date: str


class PatientResponse(PatientCreate):
    id: int

    class Config:
        orm_mode = True


# Initialize FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins. Change this to restrict origins (e.g., ["http://localhost:8000"])
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (e.g., GET, POST)
    allow_headers=["*"],  # Allows all headers
)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# CRUD Endpoints

# Create a new patient
@app.post("/patients", response_model=PatientResponse)
def create_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    db_patient = db.query(Patient).filter((Patient.phone == patient.phone) | (Patient.email == patient.email)).first()
    if db_patient:
        raise HTTPException(status_code=400, detail="Patient with this phone or email already exists")

    new_patient = Patient(**patient.dict())
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient


# Read all patients
@app.get("/patients", response_model=List[PatientResponse])
def get_patients(db: Session = Depends(get_db)):
    return db.query(Patient).all()


# Read a specific patient by ID
@app.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


# Update a patient by ID
@app.put("/patients/{patient_id}", response_model=PatientResponse)
def update_patient(patient_id: int, patient: PatientCreate, db: Session = Depends(get_db)):
    db_patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Update fields
    for key, value in patient.dict().items():
        setattr(db_patient, key, value)

    db.commit()
    db.refresh(db_patient)
    return db_patient


# Delete a patient by ID
@app.delete("/patients/{patient_id}", response_model=dict)
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    db.delete(patient)
    db.commit()
    return {"message": "Patient deleted successfully"}



# Initialize DB tables
Base.metadata.create_all(bind=engine)
