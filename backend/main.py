import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client, Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx
from twilio.rest import Client as TwilioClient
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
twilio_client = TwilioClient(TWILIO_SID, TWILIO_AUTH) if TWILIO_SID else None

class Appointment(BaseModel):
    id: Optional[int] = None
    customer_name: str
    phone_number: str
    appointment_time: datetime
    reminder_sent: bool = False

async def send_whatsapp_message(to: str, template_name: str, variables: List[str]):
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en_US"},
            "components": [{
                "type": "body",
                "parameters": [{"type": "text", "text": v} for v in variables]
            }]
        }
    }
    
    print(f"DEBUG: Sending Meta Payload: {payload}")
    
    if not WHATSAPP_TOKEN:
        print("SIMULATION MODE: Logged payload above")
        return

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200 and twilio_client:
                await send_sms_fallback(to, f"Confirm: {variables[0]} your appointment is scheduled at {variables[1]}")
        except Exception:
            if twilio_client:
                await send_sms_fallback(to, f"Confirm: {variables[0]} your appointment is scheduled at {variables[1]}")

async def send_sms_fallback(to: str, message: str):
    if twilio_client:
        twilio_client.messages.create(body=message, from_=TWILIO_NUMBER, to=to)

@app.post("/appointments")
async def create_appointment(appointment: Appointment, background_tasks: BackgroundTasks):
    data = appointment.model_dump(exclude={"id"})
    data["appointment_time"] = data["appointment_time"].isoformat()
    result = supabase.table("appointments").insert(data).execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to save appointment")
    
    background_tasks.add_task(
        send_whatsapp_message, 
        appointment.phone_number, 
        "appointment_confirmation", 
        [appointment.customer_name, appointment.appointment_time.strftime("%Y-%m-%d %H:%M")]
    )
    return result.data[0]

@app.get("/appointments", response_model=List[Appointment])
async def list_appointments():
    result = supabase.table("appointments").select("*").execute()
    return result.data

async def check_reminders():
    now = datetime.utcnow()
    one_hour_later = now + timedelta(hours=1)
    
    result = supabase.table("appointments").select("*")\
        .filter("reminder_sent", "eq", False)\
        .filter("appointment_time", "gte", now.isoformat())\
        .filter("appointment_time", "lte", one_hour_later.isoformat())\
        .execute()
    
    for apt in result.data:
        await send_whatsapp_message(
            apt["phone_number"], 
            "appointment_reminder", 
            [apt["customer_name"], apt["appointment_time"]]
        )
        supabase.table("appointments").update({"reminder_sent": True}).eq("id", apt["id"]).execute()

@app.on_event("startup")
async def startup_event():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_reminders, 'interval', seconds=60)
    scheduler.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
