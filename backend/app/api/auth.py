"""auth.py — /auth/* routes: OTP request and OTP verify."""
from fastapi import APIRouter

router = APIRouter()

# Phase 1 will implement these fully.
# Stubs here so main.py can import without error during Phase 0.

@router.post("/otp/request")
async def otp_request():
    return {"status": "not_implemented_yet"}

@router.post("/otp/verify")
async def otp_verify():
    return {"status": "not_implemented_yet"}
