from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
from mysql.connector import Error

app = FastAPI()

# Database connection
def create_connection():
    return mysql.connector.connect(
        host="localhost",   # e.g., "localhost" or IP address
        user="root",
        password="root",
        database="patient_db"
    )

# Pydantic model for request body
class Patient(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str  # Format: 'YYYY-MM-DD'
    gender: str
    phone: str
    email: str
    address: str = None  # Optional

@app.post("/add_patient")
async def add_patient(patient: Patient):
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Insert patient data into the Patients table
        insert_query = """
        INSERT INTO Patients (FirstName, LastName, DateOfBirth, Gender, Phone, Email, Address)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            patient.first_name,
            patient.last_name,
            patient.date_of_birth,
            patient.gender,
            patient.phone,
            patient.email,
            patient.address
        ))
        conn.commit()

        return {"message": "Patient added successfully", "patient_id": cursor.lastrowid}

    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
