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

