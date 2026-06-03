# WhatsApp Appointment Reminder System

A full-stack system designed to provide automated appointment confirmations and reminders via WhatsApp Cloud API with Twilio SMS fallback.

## Tech Stack
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL with Realtime)
- **Messaging**: WhatsApp Cloud API, Twilio SMS
- **Scheduling**: APScheduler

## Core Features
1. **Appointment Management**: POST endpoint to capture customer name, phone, and time.
2. **Instant Confirmation**: Automatic triggers to WhatsApp Cloud API upon successful booking.
3. **Automated Reminders**: Background worker checks every 60 seconds for upcoming appointments (within 1 hour) and sends reminders.
4. **Resiliency**: Twilio fallback for non-WhatsApp users.
5. **Real-time Dashboard**: Live updates via Supabase WebSockets.

## Project Structure
- `backend/`: FastAPI application logic, database models, and messaging services.
- `frontend/`: Simple dashboard for viewing and managing appointments.

## Setup
1. Configure environment variables in `.env`.
2. Install dependencies: `pip install -r backend/requirements.txt`.
3. Run the backend: `uvicorn backend.main:app --reload`.
