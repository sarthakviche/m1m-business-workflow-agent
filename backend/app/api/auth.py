"""
auth.py — Authentication routes.

Phase 1:
- Request OTP
- Verify OTP

For development, OTPs are stored in memory.
Production SMS delivery and persistent OTP storage
will be added in a later phase.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import OTPRequest, OTPVerify


router = APIRouter()


# ---------------------------------------------------------
# DEVELOPMENT OTP STORAGE
# ---------------------------------------------------------

# Example:
# {
#     "9876543210": {
#         "otp": "123456",
#         "expires_at": datetime(...)
#     }
# }
#
# This is intentionally in-memory for Phase 1.
# It will later be replaced with Redis/database storage.

otp_store: dict[str, dict] = {}


# ---------------------------------------------------------
# OTP REQUEST
# ---------------------------------------------------------

@router.post("/otp/request")
async def otp_request(data: OTPRequest):
    """
    Generate an OTP for the supplied phone number.

    Development behaviour:
    - Generates a fixed OTP: 123456
    - Stores it temporarily in memory
    - Returns a development response

    Production:
    - Generate a random OTP
    - Store a hashed OTP
    - Send the OTP through an SMS provider
    """

    phone = data.phone

    otp = "123456"

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    otp_store[phone] = {
        "otp": otp,
        "expires_at": expires_at,
    }

    return {
        "status": "otp_sent",
        "message": "OTP generated successfully.",
        "expires_in_seconds": 300,
        "development_otp": otp,
    }


# ---------------------------------------------------------
# OTP VERIFY
# ---------------------------------------------------------

@router.post("/otp/verify")
async def otp_verify(data: OTPVerify):
    """
    Verify the OTP supplied by the user.
    """

    phone = data.phone
    otp = data.otp

    stored = otp_store.get(phone)

    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No OTP request found for this phone number.",
        )

    # Check expiration
    if datetime.now(timezone.utc) > stored["expires_at"]:

        del otp_store[phone]

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired.",
        )

    # Check OTP
    if otp != stored["otp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP.",
        )

    # OTP is valid.
    del otp_store[phone]

    return {
        "status": "verified",
        "message": "OTP verified successfully.",
        "phone": phone,
    }