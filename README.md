# America's Got Talent Voting System

A simplified, fraud-resistant voting system built with React and FastAPI.

## Features

### Frontend (React)
- Single-page voting interface with one text input
- FingerprintJS integration for device identification
- Automatic token management and refresh
- Success/error message display
- Vote counter (max 3 votes per device)

### Backend (FastAPI)
- **Token-based authentication**: Short-lived tokens (15 min) bound to device fingerprints
- **Vote integrity enforcement**:
  - One vote per contestant per device
  - Maximum 3 total votes per device
  - Duplicate vote prevention
- **Fraud prevention**:
  - Device fingerprinting (SHA-256 hash of visitorId + localId)
  - IP-based rate limiting (Redis)
  - Suspicious pattern detection
  - CAPTCHA fallback for high-risk cases (extensible)
  - SMS verification support (extensible)

## Architecture

### Data Flow

```
1. Frontend loads → FingerprintJS generates visitorId + local UUID
2. GET /token?visitorId=...&localId=... → Server returns {token, fingerprint, expires_at}
3. Token stored in localStorage
4. User submits vote → POST /vote with X-Vote-Token header
5. Server validates token, fingerprint, contestant, and fraud checks
6. Vote recorded or error returned
```

### Security Measures

1. **Device Fingerprinting**: Server-side SHA-256 hash of client identifiers
2. **Token Expiry**: 15-minute token validity with auto-refresh
3. **Rate Limiting**: IP-based throttling (5 votes/min default)
4. **Duplicate Prevention**: Database constraints on fingerprint + contestant
5. **Vote Limits**: Maximum 3 votes per device tracked in session
6. **Suspicious Activity Flagging**: Rapid voting patterns detected and logged

## Tech Stack

- **Frontend**: React 18, Vite, FingerprintJS
- **Backend**: FastAPI, SQLAlchemy, Redis
- **Database**: PostgreSQL 14+
- **Caching**: Redis for raapi.js:1 
        
        
       GET https://www.gstatic.com/recaptcha/releases/naPR4A6FAh-yZLuCX253WaZq/recaptcha__en.js net::ERR_NETWORK_CHANGED 200 (OK)te limiting and session management

## Setup Instructions

### Prerequisites

- Python 3.9+
- Node.js 18+
- Redis server

### Backend Setup

```bashapi.js:1 
        
        
       GET https://www.gstatic.com/recaptcha/releases/naPR4A6FAh-yZLuCX253WaZq/recaptcha__en.js net::ERR_NETWORK_CHANGED 200 (OK)
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start Redis (if not already running)
# On macOS: brew services start redis
# On Linux: sudo systemctl start redis
# On Windows: Download and run Redis for Windows

# Run the server
python main.py
```

Backend will run on `http://localhost:8000`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
api.js:1 
        
        
       GET https://www.gstatic.com/recaptcha/releases/naPR4A6FAh-yZLuCX253WaZq/recaptcha__en.js net::ERR_NETWORK_CHANGED 200 (OK)
# Start development server
npm run dev
```

Frontend will run on `http://localhost:3000`

### Testing the System

1. Open `http://localhost:3000` in your browser
2. Enter a contestant last name (e.g., "Smith")
3. Click "Submit Vote"
4. You can vote for up to 3 different contestants
5. Try voting twice for theapi.js:1 
        
        
       GET https://www.gstatic.com/recaptcha/releases/naPR4A6FAh-yZLuCX253WaZq/recaptcha__en.js net::ERR_NETWORK_CHANGED 200 (OK) same contestant (should fail)
6. Try voting more than 3 times total (should fail)

## API Endpoints

### GET /token
Get a session token for voting.

**Query Parameters:**
- `visitorId` (string): FingerprintJS visitor ID
- `localId` (string): Client-generated UUID

**Response:**api.js:1 
        
        
       GET https://www.gstatic.com/recaptcha/releases/naPR4A6FAh-yZLuCX253WaZq/recaptcha__en.js net::ERR_NETWORK_CHANGED 200 (OK)
```json
{
  "token": "abc123...",
  "fingerprint": "sha256hash...",
  "expires_at": "2025-11-05T12:30:00"
}
```

### POST /vote
Submit a vote for a contestant.

**Headers:**
- `X-Vote-Token`: Session token from /token endpoint

**Body:**
```json
{
  "contestant": "smith",
  "fingerprint": "sha256hash..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Vote recorded for Smith!",
  "votes_remaining": 2,
  "requires_verification": false
}
```

### GET /stats
View voting statistics (demo/admin endpoint).

**Response:**
```json
{
  "total_votes": 42,
  "total_sessions": 18,
  "suspicious_sessions": 2,
  "votes_by_contestant": {
    "smith": 10,
    "jones": 8,
    "johnson": 7
  }
}
```

## Database Schema
}
```

### GET /stats
View voting statistics (demo/admin endpoint).

**Response:**
```json

### vote_sessions
- `id`: Primary key
- `fingerprint`: Unique device identifier (SHA-256)
- `token`: Current session token
- `token_expires_at`: Token expiry timestamp
- `votes_used`: Number of votes used (max 3)
- `is_suspicious`: Flag for suspicious activity
- `created_at`, `updated_at`: Timestamps

### votes
}
```

### GET /stats
View voting statistics (demo/admin endpoint).

**Response:**
```json
- `id`: Primary key
- `fingerprint`: Device identifier
- `contestant`: Contestant name (normalized)
- `ip_address`: Voter IP
- `verified_via_captcha`: CAPTCHA verification flag
- `verified_via_sms`: SMS verification flag
- `created_at`: Timestamp

### rate_limit_logs
- `id`: Primary key
}
```

### GET /stats
View voting statistics (demo/admin endpoint).

**Response:**
```json
- `ip_address`: Source IP
- `fingerprint`: Device identifier
- `endpoint`: API endpoint
- `created_at`: Timestamp

## Configuration

Edit [backend/.env](backend/.env) to customize:

```env
# Database
DATABASE_URL=sqlite:///./voting.db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Security
TOKEN_EXPIRY_MINUTES=15
MAX_VOTES_PER_DEVICE=3
RATE_LIMIT_VOTES_PER_MINUTE=5

# Contestants (comma-separated last names)
ALLOWED_CONTESTANTS=Jones,Smith,Johnson,Williams,Brown,Davis,Miller,Wilson,Moore,Taylor
```

# Database
DATABASE_URL=sqlite:///./voting.db

## Production Considerations

### Security Enhancements
1. **HTTPS Only**: Enforce TLS in production
2. **CAPTCHA Integration**: Integrate Google reCAPTCHA or hCaptcha
3. **SMS Verification**: Integrate Twilio or AWS SNS
4. **Database**: Switch to PostgreSQL with proper indexes
5. **Redis Clustering**: Use Redis Cluster for high availability
6. **Rate Limiting**: Implement distributed rate limiting
7. **Logging**: Add structured logging (ELK stack, Datadog, etc.)
8. **Monitoring**: Add APM (Application Performance Monitoring)

### Scalability
# Database
DATABASE_URL=sqlite:///./voting.db

1. **Load Balancing**: Deploy behind NGINX or AWS ALB
2. **Horizontal Scaling**: Run multiple FastAPI instances
3. **CDN**: Serve frontend via CloudFront or similar
4. **Database Read Replicas**: For high read loads
5. **Caching Layer**: Redis for hot data, Memcached for cold data

### Fraud Prevention Upgrades
1. **Machine Learning**: Train models on voting patterns
2. **Behavioral Analysis**: Track mouse movements, typing patterns
3. **IP Reputation**: Integrate with IP quality services
4. **Proxy Detection**: Block VPNs, Tor, data centers
5. **Device Intelligence**: Use advanced fingerprinting (Canvas, WebGL)

## Development

### Run Tests
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Lint Code
```bash
# Database
DATABASE_URL=sqlite:///./voting.db

# Backend
cd backend
pylint *.py

# Frontend
cd frontend
npm run lint
```

## License

MIT License - Feel free to use for educational purposes.

## Support

For issues or questions, please open a GitHub issue.
