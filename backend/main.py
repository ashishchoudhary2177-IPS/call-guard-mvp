from typing import Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="CallGuard MVP API")

# Wildcard origins require allow_credentials=False so browsers accept the
# response from file:// pages and any localhost port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keyword -> weight. Dict order is preserved, so matches are reported in this order.
KEYWORD_WEIGHTS: Dict[str, int] = {
    "otp": 35,
    "pin": 35,
    "urgent": 25,
    "accident": 30,
    "police": 25,
    "arrest": 35,
    "transfer": 20,
    "paise": 25,
    "upi": 25,
    "jaldi": 20,
}

KEYWORD_CAP = 65
DISCLAIMER = "Decision-support score only; not a 100% guarantee."

WARNINGS = {
    "HIGH": "High risk detected. Do not share OTP or transfer money without verifying via family.",
    "MEDIUM": "Uncertain call signal. Verify identity before sharing OTP or transferring money.",
    "LOW": "No major risk signal detected in current check.",
}


class SignalRequest(BaseModel):
    transcript: str
    voice_anomaly_score: int = 15  # clamped to 0..100 inside the handler


class SignalResponse(BaseModel):
    risk_score: int
    risk_level: str  # "LOW" | "MEDIUM" | "HIGH"
    matched_phrases: List[str]
    warning: str
    disclaimer: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": "privacy-first-mvp"}


@app.post("/analyze-signal", response_model=SignalResponse)
def analyze_signal(payload: SignalRequest) -> SignalResponse:
    # Privacy: the transcript is processed in memory only. It is never
    # logged, written to disk, or stored anywhere.
    text = payload.transcript.lower()

    matched_phrases: List[str] = [kw for kw in KEYWORD_WEIGHTS if kw in text]
    raw_keyword_points = sum(KEYWORD_WEIGHTS[kw] for kw in matched_phrases)
    capped_keyword_score = min(raw_keyword_points, KEYWORD_CAP)

    clamped_voice_score = max(0, min(100, payload.voice_anomaly_score))
    risk_score = max(0, min(100, clamped_voice_score + capped_keyword_score))

    if risk_score <= 35:
        risk_level = "LOW"
    elif risk_score <= 65:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    return SignalResponse(
        risk_score=risk_score,
        risk_level=risk_level,
        matched_phrases=matched_phrases,
        warning=WARNINGS[risk_level],
        disclaimer=DISCLAIMER,
    )