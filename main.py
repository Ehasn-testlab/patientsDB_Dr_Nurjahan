from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, EmailStr, validator
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import relationship
from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

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
    medical_records = relationship("MedicalRecord", back_populates="patient", cascade="all, delete-orphan")

class MedicalRecord(Base):
    __tablename__ = "medical_records"

    record_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    diagnosis = Column(String(255), nullable=True)
    treatment = Column(String(255), nullable=True)
    prescription = Column(String(255), nullable=True)
    notes = Column(String(255), nullable=True)
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

    @validator("date_of_birth", pre=True)
    def parse_date(cls, value):
        if isinstance(value, str):
            try:
                # Parse date, allowing for single-digit month/day
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                # Try parsing with a single-digit day format
                if "-" in value:
                    parts = value.split("-")
                    if len(parts[2]) == 1:  # if day is single digit
                        value = f"{parts[0]}-{parts[1]}-0{parts[2]}"
                    if len(parts[1]) == 1:  # if month is single digit
                        value = f"{parts[0]}-0{parts[1]}-{parts[2]}"
                    return datetime.strptime(value, "%Y-%m-%d").date()
            raise ValueError("Date must be in YYYY-MM-DD format")
        return value

class MedicalRecordCreate(BaseModel):
    diagnosis: str
    treatment: str
    prescription: str
    notes: Optional[str] = None
    record_date: date

    @validator("record_date", pre=True)
    def parse_date(cls, value):
        if isinstance(value, str):
            try:
                # Parse date, allowing for single-digit month/day
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                # Try parsing with a single-digit day format
                if "-" in value:
                    parts = value.split("-")
                    if len(parts[2]) == 1:  # if day is single digit
                        value = f"{parts[0]}-{parts[1]}-0{parts[2]}"
                    if len(parts[1]) == 1:  # if month is single digit
                        value = f"{parts[0]}-0{parts[1]}-{parts[2]}"
                    return datetime.strptime(value, "%Y-%m-%d").date()
            raise ValueError("Date must be in YYYY-MM-DD format")
        return value

class MedicalRecordResponse(MedicalRecordCreate):
    record_id: int


class PatientResponse(PatientCreate):
    id: int
    medical_records: List[MedicalRecordResponse] = []

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
@app.post("/patients/", response_model=PatientResponse)
async def create_patient(patient: PatientCreate, db: AsyncSession = Depends(get_db)):
    db_patient = Patient(**patient.dict())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

# Read patient details, including medical records
@app.get("/patients/{patient_id}", response_model=PatientResponse)
async def read_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    result = db.execute(select(Patient).filter(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

# Update a patient's details
@app.put("/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: int, patient: PatientCreate, db: AsyncSession = Depends(get_db)):
    result = db.execute(select(Patient).filter(Patient.id == patient_id))
    db_patient = result.scalar_one_or_none()
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    for key, value in patient.dict().items():
        setattr(db_patient, key, value)
    db.commit()
    db.refresh(db_patient)
    return db_patient

# Delete a patient and their medical records
@app.delete("/patients/{patient_id}")
async def delete_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    result = db.execute(select(Patient).filter(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(patient)
    db.commit()
    return {"message": "Patient deleted successfully"}

# Add a medical record for a specific patient
@app.post("/patients/{patient_id}/medical_records", response_model=MedicalRecordResponse)
async def create_medical_record(patient_id: int, record: MedicalRecordCreate, db: AsyncSession = Depends(get_db)):
    result = db.execute(select(Patient).filter(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    result = db.execute(select(MedicalRecord).filter(MedicalRecord.patient_id == patient_id))
    existing_record = result.scalar_one_or_none()
    
    if existing_record:
        # Update the existing record
        existing_record.diagnosis = record.diagnosis
        existing_record.treatment = record.treatment
        existing_record.prescription = record.prescription
        existing_record.notes = record.notes
        existing_record.record_date = record.record_date
        db.commit()
        db.refresh(existing_record)
        return MedicalRecordResponse(
            record_id=existing_record.record_id,
            patient_id=patient_id,
            diagnosis=existing_record.diagnosis,
            treatment=existing_record.treatment,
            prescription=existing_record.prescription,
            notes=existing_record.notes,
            record_date=existing_record.record_date,
        )
    else:
        new_record = MedicalRecord(**record.dict(), patient_id=patient_id)
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return MedicalRecordResponse(
            record_id=new_record.record_id,
            patient_id=patient_id,
            diagnosis=new_record.diagnosis,
            treatment=new_record.treatment,
            prescription=new_record.prescription,
            notes=new_record.notes,
            record_date=new_record.record_date,
        )
    

# Get all medical records for a specific patient
@app.get("/patients/{patient_id}/medical_records", response_model=List[MedicalRecordResponse])
async def read_medical_records(patient_id: int, db: AsyncSession = Depends(get_db)):
    result = db.execute(select(MedicalRecord).filter(MedicalRecord.patient_id == patient_id))
    records = result.scalars().all()
    return records

# Update a specific medical record
@app.put("/medical_records/{record_id}", response_model=MedicalRecordResponse)
async def update_medical_record(record_id: int, record: MedicalRecordCreate, db: AsyncSession = Depends(get_db)):
    result = db.execute(select(MedicalRecord).filter(MedicalRecord.record_id == record_id))
    db_record = result.scalar_one_or_none()
    if db_record is None:
        raise HTTPException(status_code=404, detail="Medical record not found")
    for key, value in record.dict().items():
        setattr(db_record, key, value)
    db.commit()
    db.refresh(db_record)
    return db_record

# Delete a specific medical record
@app.delete("/medical_records/{record_id}")
async def delete_medical_record(record_id: int, db: AsyncSession = Depends(get_db)):
    result = db.execute(select(MedicalRecord).filter(MedicalRecord.record_id == record_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Medical record not found")
    db.delete(record)
    db.commit()
    return {"message": "Medical record deleted successfully"}



# Initialize DB tables
Base.metadata.create_all(bind=engine)
