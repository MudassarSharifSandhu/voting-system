# ✅ Updated Improved Design — America's Got Talent Voting System
_Last updated: 2025-11-05 13:03_

> This document integrates the original design with two approved enhancements:
> 1) **Improve Token Protection** and 2) **Strong Fingerprinting Approach**.
> It supersedes overlapping parts of the original design to reflect the finalized approach for the test assignment.

## 🌟 Overview
This project is a simple **America’s Got Talent voting system** built using **React (frontend)** and **FastAPI (backend)**.

It lets users vote safely and fairly by using a **secure fingerprint** for each device and **short‑lived tokens** managed by the server. The backend makes sure each device can vote only once per contestant and a maximum of three times overall. It also checks for suspicious behavior using caching and rate limiting.

## 🔧 Key Improvements (Merged)
1. **Server‑Managed, Short‑Lived Tokens** — rotate every ~15 minutes; backend remains source of truth for identity and vote counters. (Prevents resets via storage clearing or incognito.)
2. **Strong Device Fingerprint** — `fingerprint = sha256(visitorId + localId)` combining FingerprintJS `visitorId` with an app‑generated persistent `localId`.
3. **Fingerprint‑First Enforcement** — vote limits and duplicate checks apply to the **fingerprint**, independent of token churn.
4. **Redis‑Backed Performance** — cache fingerprint sessions/tokens and apply IP/fingerprint rate limits, with adaptive CAPTCHA/SMS fallback.

## 🛠️ High-Level System Diagram
```
                🔸 React Frontend
       (Vote Form + /token initialization with visitorId/localId)
                        |
                        v
                🔸 FastAPI Backend
                + /token - Issue short-lived token (tied to fingerprint)
                + /vote  - Validate & Record Vote
                + Rate Limiter (Redis)
                + Fraud Detection Logic
                        |
        🔹 PostgreSQL / SQLite       🔹 Redis Cache
  (vote_sessions, votes, activity)   (rate limits, sessions)
```

## 1) Frontend (React + FastAPI Integration)
**Responsibilities:**
- On first load, obtain **visitorId** (FingerprintJS) and generate/persist **localId** (UUID).
- Call `GET /token?visitorId=...&localId=...` to initialize server session.
- Store `{token, fingerprint, token_expires_at}` in `localStorage`.
- On submit, send vote to `/vote` with header `X-Vote-Token` and body `{ contestant, fingerprint }`.
- If token is expired, auto-refresh via `/token` before re-submitting.

**Data Flow:**
1. `GET /token?visitorId&localId` → receive `{ token (short‑lived), fingerprint, expires_at }`
2. Store them in browser (localStorage)
3. `POST /vote` with `contestant`, `fingerprint`, header `X-Vote-Token: <token>`
4. Handle success/error only in UI

## 2) Backend (FastAPI)
### 2.1 `/token` (Short‑Lived, Server‑Managed)
**Purpose:** Issue a short‑lived token **bound to a persistent device fingerprint**.

**Steps:**
- Accept `visitorId` and `localId` from frontend.
- Compute `fingerprint = sha256(visitorId + localId)` (server‑side).
- Look up existing `vote_sessions` by fingerprint:
  - If found → **reuse** existing session and `votes_used`.
  - If not found → **create** a new session with `votes_used = 0`.
- Generate a new random token (e.g., `secrets.token_hex(16)`), **expires in ~15 minutes**.
- Persist mapping `{fingerprint → token, expires_at}` (DB and/or Redis).
- Return `{ token, fingerprint, expires_at }`.

### 2.2 `/vote` (Validate & Record)
**Validation:**
1. Verify `X-Vote-Token` exists, is **valid** and **unexpired**, and maps to the supplied `fingerprint`.
2. Normalize last name (trim/lowercase); validate against allowed list (if applicable).
3. Enforce **no duplicate vote per contestant** for this fingerprint.
4. Enforce **≤ 3 total votes** per fingerprint.
5. Apply **IP‑aware rate limiting** (Redis) and throttle suspicious bursts.
6. On high‑risk events, require **CAPTCHA or SMS** verification.
7. Record valid vote in DB and optionally cache counters in Redis.

## 3) Data Model
| Table | Fields | Purpose |
|---|---|---|
| **vote_sessions** | id, fingerprint (unique), votes_used, created_at, updated_at | Persistent device session (authoritative identity) |
| **tokens** | id, fingerprint (fk), token, expires_at, created_at | Short‑lived tokens tied to a fingerprint |
| **votes** | id, fingerprint, contestant, timestamp | Each recorded vote |
| **suspicious_activity** | id, ip, fingerprint, reason, metadata, timestamp | Fraud signals / audit trail |

**Indexes:**
- `vote_sessions.fingerprint` (unique)
- `tokens.fingerprint`, `tokens.token`, `tokens.expires_at`
- `votes.fingerprint`, `votes.contestant`
- `suspicious_activity.ip`, `suspicious_activity.fingerprint`

## 4) Security & Fraud Controls
- **Strong fingerprint:** Uses both the browser’s `visitorId` (from FingerprintJS) and an app-created `localId`, combined and hashed using SHA‑256.
- **Server-managed short tokens:** The backend creates tokens that expire after about 15 minutes. Each token is tied to a fingerprint, so it can’t be reused by others.
- **Fingerprint-based voting limits:** Each device can vote for a contestant only once and up to three times total.
- **Replay protection:** The backend verifies the token and fingerprint for every request.
- **Rate limiting:** Uses Redis to track how many requests come from each IP or fingerprint.
- **Adaptive challenge:** If a device sends too many requests too quickly, it can trigger a CAPTCHA or SMS check.
- **Audit logging:** Suspicious activity (e.g., fast repeat votes or IP spikes) is stored for future review.

## 5) API Contract (Updated)
### `GET /token?visitorId=<id>&localId=<uuid>`
**Response:**
```json
{
  "token": "abc123ef456",
  "fingerprint": "3b09a6af9b7c...",
  "expires_at": "2025-11-05T15:00:00Z"
}
```

### `POST /vote`
**Headers:**
- `X-Vote-Token: abc123ef456`

**Request:**
```json
{
  "contestant": "smith",
  "fingerprint": "3b09a6af9b7c..."
}
```

**Success:**
```json
{ "message": "Vote recorded for smith!" }
```

**Errors (examples):**
```json
{ "detail": "Token expired" }
{ "detail": "Already voted for this contestant" }
{ "detail": "Vote limit reached" }
{ "detail": "Rate limited — try again later" }
```

## 6) Reference Pseudocode
```python
# /token
def get_token(visitor_id: str, local_id: str, ip: str, ua: str):
    fingerprint = sha256(f"{visitor_id}{local_id}")
    session = db.find_session(fingerprint) or db.create_session(fingerprint)
    token = secrets.token_hex(16)
    expires_at = now_utc() + timedelta(minutes=15)
    db.save_token(fingerprint, token, expires_at)
    cache.set(f"tok:{token}", {"fp": fingerprint, "exp": expires_at}, ttl=900)
    return {"token": token, "fingerprint": fingerprint, "expires_at": expires_at}

# /vote
def post_vote(contestant: str, fingerprint: str, token: str, ip: str):
    # Basic checks
    t = cache.get(f"tok:{token}") or db.find_token(token)
    assert t and t["exp"] > now_utc() and t["fp"] == fingerprint, "invalid/expired token"
    # Rate limit
    if limiter.too_many(ip=ip, fp=fingerprint): raise HTTP429
    # Business rules
    if db.has_voted(fingerprint, contestant): raise Duplicate
    if db.total_votes(fingerprint) >= 3: raise LimitReached
    # Record
    db.insert_vote(fingerprint, contestant)
    db.increment_votes_used(fingerprint)
    return {"message": f"Vote recorded for {contestant}!"}
```

## 7) Ops & Deployment
- **Redis** for rate limiters and hot session/token lookups.
- **SQLite** for local testing; **PostgreSQL** recommended in CI/production.
- **Uvicorn** workers behind Nginx; CDN for frontend.
- **Docker** images; env‑driven config; 12‑factor ready.

## 8) Tests & Quality Gates
- Unit tests: token issuance/expiry, fingerprint mapping, vote rules.
- Integration tests: happy path, duplicate per contestant, cap at 3, rate limiter.
- Abuse simulations: high‑frequency attempts from same IP/fingerprint → CAPTCHA gate.
- Agentic audit artifacts:
  - `design_agent_output.md` (design by Agent A)
  - `design_review.md` (review by Agent B)
  - `implementation_logs/` (Agent C code gen after human approval)
  - Cloud-Code logs including prompts/iterations

## 9) Backward Compatibility / Migration
- Existing sessions continue; new `tokens` table is additive.
- Frontend auto-refreshes tokens when 401/419 detected to minimize UX friction.


---

### Appendix A — Original Design (for traceability)

# 🏛️ America's Got Talent Voting System Architecture (React + FastAPI)

## 🌟 Overview
This document describes the complete system architecture for a simplified "America's Got Talent" voting system built using **React (Frontend)** and **FastAPI (Backend)**.

The system ensures fair voting through device-level identity (token + fingerprint), enforces voting limits, and uses caching and rate-limiting to prevent abuse.

---

## 🛠️ High-Level System Diagram
```
                🔸 React Frontend
                (Vote Form + /token Initialization)
                        |
                        v
                🔸 FastAPI Backend
                + /token - Generate Token & Fingerprint
                + /vote  - Validate & Record Vote
                + Rate Limiter (Redis)
                + Fraud Detection Logic
                        |
        🔹 PostgreSQL / SQLite       🔹 Redis Cache
        (votes, sessions, logs)      (rate limits, throttling)
```

---

## ⚙️ Components

### 1. **Frontend (React)**
**Responsibilities:**
- Call `/token` when the app loads (first visit)
- Store `{token, fingerprint}` in `localStorage`
- Submit votes via `/vote` endpoint
- Display success or error messages

**Data Flow:**
1. `GET /token` → receive `{token, fingerprint}`
2. Store them in browser
3. When voting → `POST /vote` with `contestant` and `fingerprint`
4. Include token in request header: `X-Vote-Token`

**Example:**
```js
const token = localStorage.getItem("vote_token");
const fingerprint = localStorage.getItem("fingerprint");

fetch("/vote", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Vote-Token": token
  },
  body: JSON.stringify({ contestant, fingerprint })
});
```

---

### 2. **Backend (FastAPI)**
**Core Responsibilities:**
1. Token Service (`/token`) — identifies each device
2. Voting Service (`/vote`) — records and validates votes
3. Rate Limiting and Fraud Detection
4. Persistent Storage (DB + Redis)

#### 2.1 `/token` Endpoint
**Purpose:** Generate device identity.

**Steps:**
- Extract `User-Agent` and `IP`
- Compute fingerprint: `sha256(ip + user-agent)`
- Generate random token: `secrets.token_hex(16)`
- Store `(token, fingerprint)` in DB
- Return both to frontend

**Response:**
```json
{
  "token": "abc123ef456",
  "fingerprint": "4acddf9f2abf1a0..."
}
```

#### 2.2 `/vote` Endpoint
**Purpose:** Accept and record votes safely.

**Validation Steps:**
1. Check if token and fingerprint are valid
2. Ensure no duplicate vote for same contestant
3. Ensure no more than 3 total votes for device
4. Apply IP-based rate limit
5. Record valid vote in database

**Possible Responses:**
```json
{ "message": "Vote recorded for smith!" }
```
```json
{ "detail": "Already voted for this contestant" }
```

---

### 3. **Rate Limiting & Caching (Redis)**
Used to detect and throttle spam requests.

**Example:**
```
rate_limit:192.168.0.12 -> 5 (requests in last 10 seconds)
```
If a user exceeds threshold → temporarily blocked.

**Library:** `slowapi` or custom FastAPI middleware.

---

### 4. **Database (PostgreSQL / SQLite)**
Stores persistent vote and session data.

| Table | Fields | Purpose |
|--------|---------|----------|
| **vote_sessions** | id, token, fingerprint, created_at | Represents unique device session |
| **votes** | id, token, fingerprint, contestant, timestamp | Each recorded vote |
| **suspicious_activity** | id, ip, fingerprint, reason, timestamp | Optional fraud logs |

---

### 5. **Security Layers**
| Concern | Defense |
|----------|----------|
| Token spoofing | Tokens verified against fingerprints |
| Multiple votes | 3-vote limit per token |
| IP spam | Redis-based throttling |
| Replay attacks | Token expiry after contest |
| Bots | CAPTCHA or SMS fallback |

---

## 📊 Data Flow Summary

| Step | Actor | Action |
|------|--------|--------|
| 1 | Frontend | Calls `/token` and stores token/fingerprint |
| 2 | Frontend | User submits vote `/vote` with token & fingerprint |
| 3 | Backend | Validates and enforces rules |
| 4 | Backend | Saves to DB if valid |
| 5 | Redis | Throttles excessive IPs |
| 6 | Backend | Responds with success/error |

---

## 🔐 Security & Fraud Control
- Device-based fingerprinting (IP + User-Agent)
- Enforced 3-vote-per-device rule
- Duplicate-vote prevention
- Rate limiting (Redis)
- CAPTCHA for suspicious patterns
- Logging all attempts in `suspicious_activity`

---

## 🏢 Deployment Architecture
```
┌────────────────────────────┐
│   React App (Vercel/CDN)   │
└────────────┬───────────────┘
             │
┌────────────▼───────────────┐
│   Nginx Reverse Proxy       │
│   Routes /api → FastAPI     │
└────────────┬───────────────┘
             │
┌────────────▼───────────────┐
│ FastAPI + Uvicorn Server   │
│ - /token, /vote, rate limit│
└────────────┬───────────────┘
             │
 ┌───────────▼───────────┐     ┌───────────▼───────────┐
 │ PostgreSQL / SQLite DB │     │ Redis Cache           │
 │ Votes, Sessions        │     │ IP rate limiting data │
 └────────────────────────┘     └───────────────────────┘
```

---

## 🌐 API Contract

### `GET /token`
**Response:**
```json
{
  "token": "abc123ef456",
  "fingerprint": "4acddf9f2abf1a0..."
}
```

### `POST /vote`
**Request:**
```json
{
  "contestant": "smith",
  "fingerprint": "4acddf9f2abf1a0..."
}
```
**Header:** `X-Vote-Token: abc123ef456`

**Response:**
```json
{ "message": "Vote recorded for smith!" }
```
**Error:**
```json
{ "detail": "Already voted for this contestant" }
```

---

## 🔧 Tech Stack Summary
| Layer | Technology |
|--------|-------------|
| Frontend | React + Fetch API |
| Backend | FastAPI + Uvicorn |
| Database | SQLite (test) / PostgreSQL (prod) |
| Cache | Redis (rate limit + temp block) |
| Middleware | SlowAPI / custom throttle logic |
| Security | SHA256 hashing, IP tracking, CAPTCHA fallback |
| Deployment | Docker + Nginx reverse proxy |

---

## 🌐 Summary
✅ Token + Fingerprint = Device identity  
✅ 3-vote cap per device  
✅ Redis = rate-limiting and caching  
✅ CAPTCHA for abuse  
✅ Logs for suspicious IPs  
✅ Clean separation: `/token` (identity) and `/vote` (action)

---

**This architecture is production-ready for your test assignment and clearly demonstrates**:
- disciplined endpoint design,
- structured backend validation,
- anti-fraud logic,
- and clean frontend–backend interaction.



---

### Appendix B — Improve Token Protection (source)

# 🔐 Improved System Protection & Token Management

## ⚠️ Problem
Currently, the system enforces a 3-vote limit per device using a **token + fingerprint** combination. The token is stored in the browser's localStorage. However, if users clear their localStorage or use incognito mode, they can reset their token and effectively appear as a new device. This bypasses the vote limit.

---

## 🧠 Root Cause
- The **token** is client-side only (stored in localStorage).
- The **backend** issues a new token every time `/token` is called.
- There is no persistent server-side mapping to connect multiple tokens to the same fingerprint.

As a result, the backend cannot distinguish between a returning user who cleared their localStorage and a genuinely new device.

---

## 🛠️ Proposed Solution
To strengthen system integrity, use **server-managed tokens** and **fingerprint-based validation**:

### 1. Fingerprint as the true identity
- Treat the **fingerprint (visitorId + localId)** as the permanent identity.
- When a new `/token` request is made:
  - The backend checks if the fingerprint already exists.
  - If it exists → reuse the existing session and vote count.
  - If not → create a new record.

### 2. Short-lived tokens
- Make tokens expire (e.g., 15 minutes).
- The frontend must refresh tokens periodically.
- Each new token is tied to the same fingerprint session.

This ensures that even if the token is deleted, the backend still recognizes the device via its fingerprint.

### 3. Server-side mapping
Maintain a mapping between **fingerprint → token → vote count**.

| fingerprint | token | expires_at | votes_used |
|--------------|--------|-------------|-------------|
| 3f84aa... | abc123 | 2025-11-05 15:00 | 2 |

If a fingerprint already exists, the backend reuses that record instead of issuing a completely new identity.

### 4. Optional Redis caching
- Cache fingerprints and token metadata in Redis for faster validation.
- Example:
  ```
  fingerprint:3f84aa... → { votes_used: 2, last_vote: '2025-11-05T14:32' }
  ```

### 5. Token verification workflow
1. Frontend sends `/token` with fingerprint.
2. Backend checks existing record:
   - Found → return existing session data.
   - Not found → create new record.
3. On `/vote`:
   - Verify token is valid and not expired.
   - Count votes linked to fingerprint.
   - Enforce 3-vote cap regardless of token resets.

So the new flow would be:

Frontend sends visitorId + localId to /token.

Backend hashes → gets fingerprint.

Backend looks for existing fingerprint in DB:

If found → return the same session or reuse existing vote count.

If not found → create new record and issue new token.

Backend stores token expiry (short-lived, e.g. 15 min).

On every /vote, backend checks fingerprint’s total votes, not just token.

---

## 🧱 Benefits
| Improvement | Description |
|--------------|-------------|
| Persistent fingerprint tracking | Prevents vote reset even if user clears localStorage. |
| Short-lived tokens | Reduces attack window for token reuse or spoofing. |
| Server validation | Backend always maintains authority on user identity. |
| Redis cache | Boosts performance and reduces DB queries. |

---

## ✅ Outcome
By shifting token validation to the backend and reusing fingerprint records:
- Users **cannot reset votes** by clearing browser storage.
- The system remains **resilient** to casual manipulation.
- Voting remains **fair and auditable** across sessions and browsers.



---

### Appendix C — Strong Fingerprinting Approach (source)

# 💪 America's Got Talent Voting System Architecture (Strong Fingerprinting Version)

## 🌟 Overview
This version implements the **Strong Fingerprinting Approach** to provide secure, fair, and tamper-resistant voting enforcement.

It combines:
- **FingerprintJS `visitorId`** → A stable browser/device fingerprint based on 20+ unique attributes (browser, hardware, screen, timezone, GPU, etc.).
- **Persistent `localId`** → A random UUID stored in localStorage or cookies.

Together, these form a **unique, privacy-safe device identity** that makes cheating (extra votes, VPN use, or browser resets) extremely difficult.

---

## 🔐 Strong Fingerprinting Mechanism
- When the user first opens the site, the frontend generates:
  - A **visitorId** from FingerprintJS.
  - A **localId** stored persistently in localStorage or cookies.
- The frontend sends both to the backend via `/token`.
- The backend combines and hashes them:
  ```
  sha256(visitorId + localId)
  ```
- This hash becomes the **fingerprint**, a permanent device identifier.

---

## 🧩 Key Features
| Component | Role | Example |
|------------|------|----------|
| `visitorId` | Generated by FingerprintJS, captures device/browser characteristics | `8c7b8f3f2c4b71e9...` |
| `localId` | Random UUID stored by your app in localStorage | `b2c47f12-d4a6-4b3f...` |
| `sha256(visitorId + localId)` | Combined server-side to form unique device fingerprint | `3b09a6af9b7c...` |

---

## 🧱 Database & Server Logic
- Each fingerprint maps to a device entry in the `vote_sessions` table.
- The backend uses this fingerprint to:
  - Enforce **max 3 votes per device**.
  - Prevent duplicate votes for the same contestant.
  - Detect suspicious voting or device spoofing.
- Even if the user clears cookies or changes IP, the same fingerprint ensures consistent tracking.

---

## 🧠 Why This Approach is Strong
| Benefit | Description |
|----------|--------------|
| **High Stability** | FingerprintJS uses multiple browser & hardware signals, so minor changes (like IP or browser version) don’t affect identity. |
| **Persistence** | localId ensures the same user remains identifiable across sessions. |
| **Privacy-Safe** | All data is hashed before storage; no personal info is kept. |
| **Anti-Fraud Enforcement** | Each fingerprint can vote only 3 times total, once per contestant. |
| **Resilience to Cheating** | Clearing storage or using VPN won’t reset voting rights. |

---

## ✅ Final Outcome
- Each device = **one stable, verified identity**.
- Backend controls fingerprint validation.
- Users can’t bypass vote limits without clearing all browser data **and** changing device/browser entirely.
- Ensures fair, anonymous, and secure voting integrity.

