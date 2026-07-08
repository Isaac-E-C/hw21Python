from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class PatientInfo(BaseModel):
    id: str
    fullName: str
    nationalId: str
    email: str
    phone: str
    insuranceType: str


class DoctorInfo(BaseModel):
    id: str
    fullName: str
    specialty: str
    licenseNumber: str
    rating: float
    email: str
    phone: str


class TherapyInfo(BaseModel):
    id: str
    name: str
    description: str
    specialty: str
    duration: int
    price: float


class AppointmentResponse(BaseModel):
    id: str
    patientId: str
    doctorId: str
    therapyId: str
    date: str
    time: str
    status: str
    symptoms: str
    hasExams: bool
    exams: list
    cancellationReason: Optional[str] = None
    doctorNotes: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    patient: Optional[PatientInfo] = None
    doctor: Optional[DoctorInfo] = None
    therapy: Optional[TherapyInfo] = None


class AppointmentRequest(BaseModel):
    doctorId: str
    therapyId: str
    date: str
    time: str
    symptoms: str
    hasExams: bool = False
    exams: list = []


class AppointmentUpdateRequest(BaseModel):
    status: Optional[str] = None
    doctorNotes: Optional[str] = None


class CancelRequest(BaseModel):
    reason: str


class AvailableSlot(BaseModel):
    date: str
    time: str
    available: bool
    doctorId: str


class CreateAppointmentResponse(BaseModel):
    message: str
    appointment: dict
