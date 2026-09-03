"""Authentication request and response schemas."""

from pydantic import BaseModel, Field


class OTPRequest(BaseModel):
    phone: str = Field(
        ...,
        min_length=10,
        max_length=15,
        description="User's phone number",
    )


class OTPVerify(BaseModel):
    phone: str = Field(
        ...,
        min_length=10,
        max_length=15,
        description="User's phone number",
    )

    otp: str = Field(
        ...,
        min_length=4,
        max_length=6,
        description="OTP received by the user",
    )