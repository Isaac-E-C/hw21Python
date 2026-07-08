import random
from datetime import datetime, timedelta
from bson import ObjectId
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from database import db
from models import (
    AppointmentRequest, AppointmentUpdateRequest,
    CancelRequest
)
from validators import (
    validate_date_format, validate_time_format,
    validate_min_anticipation, validate_cancellation_lead_time
)
from seed_data import patients_data, doctors_data, therapies_data, symptoms_list

router = APIRouter()


def serialize_doc(doc):
    if doc is None:
        return None
    doc["id"] = str(doc.pop("_id"))
    return doc


async def get_patient(patient_id):
    doc = await db.patients.find_one({"_id": ObjectId(patient_id)})
    return serialize_doc(doc)


async def get_doctor(doctor_id):
    doc = await db.doctors.find_one({"_id": ObjectId(doctor_id)})
    return serialize_doc(doc)


async def get_therapy(therapy_id):
    doc = await db.therapies.find_one({"_id": ObjectId(therapy_id)})
    return serialize_doc(doc)


@router.get("/")
async def get_appointments(
    status: str = Query(None),
    date: str = Query(None),
    patient_id: str = Query(None),
    doctor_id: str = Query(None)
):
    try:
        match = {}

        if status:
            statuses = [s.strip() for s in status.split(",")]
            if len(statuses) > 1:
                match["status"] = {"$in": statuses}
            else:
                match["status"] = statuses[0]

        if date:
            match["date"] = date

        if patient_id:
            match["patientId"] = patient_id

        if doctor_id:
            match["doctorId"] = doctor_id

        cursor = db.appointments.find(match).sort([("date", -1), ("time", -1)])
        appointments = await cursor.to_list(length=None)

        result = []
        for appt in appointments:
            appt = serialize_doc(appt)
            patient = await get_patient(appt.get("patientId", ""))
            doctor = await get_doctor(appt.get("doctorId", ""))
            therapy = await get_therapy(appt.get("therapyId", ""))
            appt["patient"] = patient
            appt["doctor"] = doctor
            appt["therapy"] = therapy
            appt["createdAt"] = appt.get("createdAt", datetime.utcnow())
            appt["updatedAt"] = appt.get("updatedAt", datetime.utcnow())
            result.append(appt)

        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/available-schedules")
async def get_available_schedules(
    doctor_id: str = Query(None),
    date: str = Query(None)
):
    if not doctor_id or not date:
        return JSONResponse(status_code=400, content={"error": "doctorId and date are required"})

    if not validate_date_format(date):
        return JSONResponse(status_code=400, content={"error": "Invalid date format (must be YYYY-MM-DD)"})

    try:
        date_dt = datetime.strptime(date, "%Y-%m-%d")
        day_of_week = date_dt.weekday()

        schedules = await db.work_schedules.find({
            "doctorId": doctor_id,
            "dayOfWeek": day_of_week,
            "active": True
        }).to_list(length=None)

        if not schedules:
            return []

        booked = await db.appointments.find({
            "doctorId": doctor_id,
            "date": date,
            "status": {"$in": ["pending", "confirmed"]}
        }).to_list(length=None)

        occupied_hours = {b.get("time") for b in booked}

        available_slots = []

        for schedule in schedules:
            start_h, start_m = map(int, schedule["startTime"].split(":"))
            end_h, end_m = map(int, schedule["endTime"].split(":"))

            curr_h, curr_m = start_h, start_m

            while curr_h < end_h or (curr_h == end_h and curr_m < end_m):
                time_str = f"{curr_h:02d}:{curr_m:02d}"

                available = True
                if time_str in occupied_hours:
                    available = False
                try:
                    validate_min_anticipation(date, time_str)
                except ValueError:
                    available = False

                available_slots.append({
                    "date": date,
                    "time": time_str,
                    "available": available,
                    "doctorId": doctor_id
                })

                curr_m += 30
                if curr_m >= 60:
                    curr_h += 1
                    curr_m = 0

        return available_slots
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/{appointment_id}")
async def get_appointment_by_id(appointment_id: str):
    try:
        appt = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
        if not appt:
            return JSONResponse(status_code=404, content={"error": "Appointment not found"})

        appt = serialize_doc(appt)
        patient = await get_patient(appt.get("patientId", ""))
        doctor = await get_doctor(appt.get("doctorId", ""))
        therapy = await get_therapy(appt.get("therapyId", ""))

        appt["patient"] = patient
        appt["doctor"] = doctor
        appt["therapy"] = therapy
        appt["createdAt"] = appt.get("createdAt", datetime.utcnow())
        appt["updatedAt"] = appt.get("updatedAt", datetime.utcnow())

        return appt
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/")
async def create_appointment(data: AppointmentRequest):
    if not data.doctorId or not data.therapyId or not data.date or not data.time or not data.symptoms:
        return JSONResponse(status_code=400, content={"error": "Missing required fields"})

    if not validate_date_format(data.date):
        return JSONResponse(status_code=400, content={"error": "Invalid date format (must be YYYY-MM-DD)"})

    if not validate_time_format(data.time):
        return JSONResponse(status_code=400, content={"error": "Invalid time format (must be HH:mm)"})

    if len(data.symptoms) < 10:
        return JSONResponse(status_code=400, content={"error": "Symptoms must be at least 10 characters long"})

    try:
        validate_min_anticipation(data.date, data.time)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    try:
        existing = await db.appointments.find_one({
            "patientId": data.doctorId,
            "date": data.date,
            "time": data.time,
            "status": {"$in": ["pending", "confirmed"]}
        })
        if existing:
            return JSONResponse(status_code=409, content={
                "error": "You already have an appointment booked at this date and time"
            })

        occupied = await db.appointments.find_one({
            "doctorId": data.doctorId,
            "date": data.date,
            "time": data.time,
            "status": {"$in": ["pending", "confirmed"]}
        })
        if occupied:
            return JSONResponse(status_code=409, content={
                "error": "This schedule is already occupied"
            })

        now = datetime.utcnow()
        appointment_doc = {
            "patientId": data.doctorId,
            "doctorId": data.doctorId,
            "therapyId": data.therapyId,
            "date": data.date,
            "time": data.time,
            "symptoms": data.symptoms,
            "hasExams": data.hasExams,
            "exams": data.exams,
            "status": "pending",
            "cancellationReason": None,
            "doctorNotes": None,
            "createdAt": now,
            "updatedAt": now
        }

        result = await db.appointments.insert_one(appointment_doc)
        appointment_doc["_id"] = result.inserted_id
        appointment_doc = serialize_doc(appointment_doc)

        patient = await get_patient(appointment_doc.get("patientId", ""))
        doctor = await get_doctor(appointment_doc.get("doctorId", ""))
        therapy = await get_therapy(appointment_doc.get("therapyId", ""))

        return JSONResponse(status_code=201, content={
            "message": "Appointment created successfully",
            "appointment": {
                "id": appointment_doc["id"],
                "date": appointment_doc["date"],
                "time": appointment_doc["time"],
                "status": appointment_doc["status"],
                "patient": patient,
                "doctor": {
                    "fullName": doctor.get("fullName") if doctor else None,
                    "specialty": doctor.get("specialty") if doctor else None
                } if doctor else None,
                "therapy": {
                    "name": therapy.get("name") if therapy else None,
                    "duration": therapy.get("duration") if therapy else None,
                    "price": therapy.get("price") if therapy else None
                } if therapy else None
            }
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.put("/{appointment_id}")
async def update_appointment(appointment_id: str, data: AppointmentUpdateRequest):
    try:
        appt = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
        if not appt:
            return JSONResponse(status_code=404, content={"error": "Appointment not found"})

        update_fields = {}
        if data.status is not None:
            update_fields["status"] = data.status
        if data.doctorNotes is not None:
            update_fields["doctorNotes"] = data.doctorNotes
        update_fields["updatedAt"] = datetime.utcnow()

        if update_fields:
            await db.appointments.update_one(
                {"_id": ObjectId(appointment_id)},
                {"$set": update_fields}
            )

        updated = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
        updated = serialize_doc(updated)

        return {
            "message": "Appointment updated successfully",
            "appointment": updated
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.delete("/{appointment_id}")
async def cancel_appointment(appointment_id: str, data: CancelRequest = None):
    reason = data.reason if data and data.reason else None
    if not reason:
        return JSONResponse(status_code=400, content={
            "error": "You must provide a cancellation reason"
        })

    try:
        appt = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
        if not appt:
            return JSONResponse(status_code=404, content={"error": "Appointment not found"})

        if appt.get("status") not in ["pending", "confirmed"]:
            return JSONResponse(status_code=400, content={
                "error": "This appointment cannot be cancelled"
            })

        try:
            validate_cancellation_lead_time(appt["date"], appt["time"])
        except ValueError as e:
            return JSONResponse(status_code=400, content={"error": str(e)})

        await db.appointments.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": {
                "status": "cancelled",
                "cancellationReason": reason,
                "updatedAt": datetime.utcnow()
            }}
        )

        cancelled = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
        cancelled = serialize_doc(cancelled)

        return {
            "message": "Appointment cancelled successfully",
            "appointment": cancelled
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/seed")
async def seed_database():
    try:
        await db.patients.delete_many({})
        await db.doctors.delete_many({})
        await db.therapies.delete_many({})
        await db.appointments.delete_many({})
        await db.work_schedules.delete_many({})

        patients_result = await db.patients.insert_many(patients_data)
        patient_ids = patients_result.inserted_ids

        doctors_result = await db.doctors.insert_many(doctors_data)
        doctor_ids = doctors_result.inserted_ids

        therapies_result = await db.therapies.insert_many(therapies_data)
        therapy_ids = therapies_result.inserted_ids

        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = base_date + timedelta(days=2)
        today = datetime.now()

        statuses = ["pending", "confirmed", "completed", "cancelled"]
        status_weights = [0.2, 0.3, 0.3, 0.2]

        appointments = []
        for i in range(25):
            day_offset = i // 4
            slot_idx = i % 4
            apt_date = start_date + timedelta(days=day_offset)
            hours = [8, 9, 10, 11, 14, 15, 16]
            hour = hours[slot_idx % len(hours)]
            minutes = [0, 30][slot_idx % 2]
            apt_time = f"{hour:02d}:{minutes:02d}"
            status = random.choices(statuses, weights=status_weights, k=1)[0]
            cancellation_reason = None
            doctor_notes = None
            if status == "cancelled":
                cancellation_reason = random.choice([
                    "Emergencia familiar", "Problemas de transporte",
                    "Cambio de horario laboral", "Malestar general"
                ])
            if status == "completed":
                doctor_notes = random.choice([
                    "Paciente responde bien al tratamiento. Continuar con ejercicios en casa.",
                    "Mejora significativa en rango de movimiento. Aumentar intensidad gradualmente.",
                    "Dolor reducido en un 60%. Mantener frecuencia de sesiones.",
                    "Buena evoluci\u00f3n. Disminuir frecuencia a una vez por semana."
                ])
            appointments.append({
                "patientId": str(patient_ids[i % len(patient_ids)]),
                "doctorId": str(doctor_ids[i % len(doctor_ids)]),
                "therapyId": str(therapy_ids[i % len(therapy_ids)]),
                "date": apt_date.strftime("%Y-%m-%d"),
                "time": apt_time,
                "status": status,
                "symptoms": symptoms_list[i % len(symptoms_list)],
                "hasExams": random.choice([True, False]),
                "exams": (["Radiograf\u00eda", "Resonancia", "Electromiograf\u00eda"][:random.randint(0, 2)]
                          if random.choice([True, False]) else []),
                "cancellationReason": cancellation_reason,
                "doctorNotes": doctor_notes,
                "createdAt": today - timedelta(days=random.randint(1, 14), hours=random.randint(0, 23)),
                "updatedAt": today - timedelta(hours=random.randint(0, 12)),
            })

        await db.appointments.insert_many(appointments)

        schedules = []
        for doctor_id in doctor_ids:
            for day in range(5):
                schedules.append({"doctorId": str(doctor_id), "dayOfWeek": day, "startTime": "08:00", "endTime": "12:00", "active": True})
                schedules.append({"doctorId": str(doctor_id), "dayOfWeek": day, "startTime": "14:00", "endTime": "17:00", "active": True})
        await db.work_schedules.insert_many(schedules)

        return {
            "message": "Database seeded successfully",
            "stats": {
                "patients": len(patients_data),
                "doctors": len(doctors_data),
                "therapies": len(therapies_data),
                "appointments": 25,
                "workSchedules": len(schedules)
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
