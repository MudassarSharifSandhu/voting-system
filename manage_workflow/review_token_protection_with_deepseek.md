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

