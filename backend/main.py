from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets


from database import (
    get_db, init_db, VoteSession, Vote, RateLimitLog, IPChangeLog
)
from redis_client import check_rate_limit, cache_set, cache_get
from config import settings
from captcha_service import captcha_service

app = FastAPI(title="AGT Voting System")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class TokenRequest(BaseModel):
    visitorId: str
    localId: str


class TokenResponse(BaseModel):
    token: str
    fingerprint: str
    expires_at: str
    votes_used: int
    votes_used_from_ip: int
    is_suspicious: bool


class VoteRequest(BaseModel):
    contestant: str
    fingerprint: str
    recaptcha_token: Optional[str] = None  # Required only if session is suspicious


class VoteResponse(BaseModel):
    success: bool
    message: str
    votes_remaining: Optional[int] = None
    requires_verification: bool = False
    requires_captcha: bool = False


# Utility functions
def compute_fingerprint(visitor_id: str, local_id: str) -> str:
    """
    Generate a SHA-256 fingerprint from visitor ID only.

    Note: We use ONLY visitorId (not localId) to ensure the fingerprint
    persists even if user clears localStorage. This prevents vote limit bypass.
    """
    return hashlib.sha256(visitor_id.encode()).hexdigest()


def generate_token() -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_hex(16)


def normalize_contestant_name(name: str) -> str:
    """Normalize contestant name for comparison"""
    return name.strip().lower()


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "AGT Voting System"}


@app.get("/token", response_model=TokenResponse)
async def get_token(
    visitorId: str,
    localId: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Issue a short-lived token bound to a persistent device fingerprint.

    Steps:
    1. Compute fingerprint from visitorId + localId
    2. Look up existing session or create new one
    3. Generate new token with expiry
    4. Return token, fingerprint, and expiry time
    """

    # Rate limiting for token endpoint
    ip = get_client_ip(request)
    rate_limit_key = f"rate_limit:token:{ip}"
    is_allowed, count = check_rate_limit(rate_limit_key, 10, 60)  # 10 requests per minute

    if not is_allowed:
        # Log rate limit violation
        log = RateLimitLog(
            ip_address=ip,
            fingerprint="N/A",
            endpoint="/token"
        )
        db.add(log)
        db.commit()
        raise HTTPException(status_code=429, detail="Too many token requests. Please try again later.")

    # Compute server-side fingerprint
    fingerprint = compute_fingerprint(visitorId, localId)

    # Look up existing session
    session = db.query(VoteSession).filter(VoteSession.fingerprint == fingerprint).first()

    # Check for IP changes when refreshing token (e.g., after network switch)
    if session and session.ip_address and session.ip_address != ip:
        # IP has changed - mark as suspicious
        ip_change_log = IPChangeLog(
            fingerprint=fingerprint,
            old_ip=session.ip_address,
            new_ip=ip
        )
        db.add(ip_change_log)
        session.is_suspicious = True

    # Generate new token
    token = generate_token()
    expires_at = datetime.utcnow() + timedelta(minutes=settings.TOKEN_EXPIRY_MINUTES)

    if session:
        # Update existing session
        session.token = token
        session.token_expires_at = expires_at
        session.updated_at = datetime.utcnow()
        session.ip_address = ip
    else:
        # Create new session
        session = VoteSession(
            fingerprint=fingerprint,
            token=token,
            token_expires_at=expires_at,
            votes_used=0,
            ip_address=ip
        )
        db.add(session)

    db.commit()

    # Cache token in Redis for fast lookup
    cache_set(f"token:{fingerprint}", token, settings.TOKEN_EXPIRY_MINUTES * 60)

    # Count total votes from this IP (across all browsers)
    votes_from_ip = db.query(Vote).filter(Vote.ip_address == ip).count()

    return TokenResponse(
        token=token,
        fingerprint=fingerprint,
        expires_at=expires_at.isoformat(),
        votes_used=session.votes_used,
        votes_used_from_ip=votes_from_ip,
        is_suspicious=session.is_suspicious
    )


@app.post("/vote", response_model=VoteResponse)
async def submit_vote(
    vote_request: VoteRequest,
    request: Request,
    x_vote_token: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Validate and record a vote.

    Validation steps:
    1. Verify token exists, is valid, and maps to fingerprint
    2. Normalize and validate contestant name
    3. Check for duplicate vote per contestant
    4. Enforce maximum votes per device (3)
    5. Apply IP-based rate limiting
    6. Flag suspicious patterns
    """

    ip = get_client_ip(request)
    fingerprint = vote_request.fingerprint
    contestant = normalize_contestant_name(vote_request.contestant)

    # Step 1: Verify token
    session = db.query(VoteSession).filter(VoteSession.fingerprint == fingerprint).first()

    if not session:
        raise HTTPException(status_code=401, detail="Invalid session. Please refresh your token.")

    if session.token != x_vote_token:
        raise HTTPException(status_code=401, detail="Invalid token. Please refresh your token.")

    if session.token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expired. Please refresh your token.")

    # Step 1.3: Check for IP changes BEFORE processing vote (detect suspicious activity early)
    if session.ip_address and session.ip_address != ip:
        # IP has changed for this fingerprint! Possible VPN switch
        # Mark as suspicious and require CAPTCHA (don't block, just require verification)

        # Log the IP change
        ip_change_log = IPChangeLog(
            fingerprint=fingerprint,
            old_ip=session.ip_address,
            new_ip=ip
        )
        db.add(ip_change_log)

        # Mark session as suspicious and require CAPTCHA verification
        session.is_suspicious = True
        session.ip_address = ip  # Update to new IP
        db.commit()

    # Step 1.5: Check if session is suspicious - require CAPTCHA verification
    if session.is_suspicious:
        # Session is suspicious - require reCAPTCHA verification
        if not vote_request.recaptcha_token:
            raise HTTPException(
                status_code=403,
                detail="CAPTCHA verification required. Please complete the reCAPTCHA challenge."
            )
        
        # Verify reCAPTCHA with client IP
        is_valid = captcha_service.verify_response(
            recaptcha_token=vote_request.recaptcha_token,
            remote_ip=ip
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=403,
                detail="Invalid CAPTCHA response. Please try again."
            )

    # Step 2: Normalize and validate contestant name
    if contestant not in settings.allowed_contestants_list:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid contestant name. Allowed contestants: {', '.join(settings.allowed_contestants_list)}"
        )

    # Step 3: Check for duplicate vote for this contestant
    existing_vote = db.query(Vote).filter(
        Vote.fingerprint == fingerprint,
        Vote.contestant == contestant
    ).first()

    if existing_vote:
        raise HTTPException(
            status_code=400,
            detail=f"You have already voted for {contestant.capitalize()}."
        )

    # Step 4: Enforce maximum votes per device
    if session.votes_used >= settings.MAX_VOTES_PER_DEVICE:
        raise HTTPException(
            status_code=403,
            detail=f"Maximum votes ({settings.MAX_VOTES_PER_DEVICE}) reached for this device."
        )

    # Step 4.5: Enforce maximum votes per IP (across all browsers/devices)
    total_votes_from_ip = db.query(Vote).filter(
        Vote.ip_address == ip
    ).count()

    if total_votes_from_ip >= settings.MAX_VOTES_PER_IP:
        # Mark all sessions from this IP as suspicious
        sessions_from_ip = db.query(VoteSession).filter(
            VoteSession.ip_address == ip
        ).all()
        for s in sessions_from_ip:
            s.is_suspicious = True
        db.commit()

        raise HTTPException(
            status_code=403,
            detail=f"Maximum votes ({settings.MAX_VOTES_PER_IP}) reached from your location. You cannot vote from multiple browsers."
        )

    # Step 5: IP-based rate limiting
    rate_limit_key = f"rate_limit:vote:{ip}"
    is_allowed, count = check_rate_limit(
        rate_limit_key,
        settings.RATE_LIMIT_VOTES_PER_MINUTE,
        60
    )

    if not is_allowed:
        # Mark session as suspicious
        session.is_suspicious = True
        db.commit()

        # Log rate limit violation
        log = RateLimitLog(
            ip_address=ip,
            fingerprint=fingerprint,
            endpoint="/vote"
        )
        db.add(log)
        db.commit()

        # In a real system, this would trigger CAPTCHA or SMS verification
        return VoteResponse(
            success=False,
            message="Suspicious activity detected. Additional verification required.",
            requires_verification=True
        )

    # Step 6: Check for suspicious patterns (multiple votes in short time)
    recent_votes = db.query(Vote).filter(
        Vote.fingerprint == fingerprint,
        Vote.created_at > datetime.utcnow() - timedelta(minutes=1)
    ).count()

    if recent_votes >= 2:
        session.is_suspicious = True
        db.commit()

    # Record the vote
    vote = Vote(
        fingerprint=fingerprint,
        contestant=contestant,
        ip_address=ip,
        verified_via_captcha=session.is_suspicious,  # True if CAPTCHA was required and verified
        verified_via_sms=False
    )
    db.add(vote)

    # Update session vote count
    session.votes_used += 1
    session.updated_at = datetime.utcnow()

    db.commit()

    votes_remaining = settings.MAX_VOTES_PER_DEVICE - session.votes_used

    return VoteResponse(
        success=True,
        message=f"Vote recorded for {contestant.capitalize()}!",
        votes_remaining=votes_remaining,
        requires_verification=False
    )


@app.get("/captcha/site-key")
async def get_captcha_site_key():
    """
    Get the reCAPTCHA site key for frontend rendering.
    """
    try:
        site_key = captcha_service.get_site_key()
        return {"site_key": site_key}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get voting statistics (for admin/demo purposes)"""
    total_votes = db.query(Vote).count()
    total_sessions = db.query(VoteSession).count()
    suspicious_sessions = db.query(VoteSession).filter(VoteSession.is_suspicious == True).count()

    # Vote counts by contestant
    from sqlalchemy import func
    contestant_votes = db.query(
        Vote.contestant,
        func.count(Vote.id).label("count")
    ).group_by(Vote.contestant).all()

    return {
        "total_votes": total_votes,
        "total_sessions": total_sessions,
        "suspicious_sessions": suspicious_sessions,
        "votes_by_contestant": {name: count for name, count in contestant_votes}
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
