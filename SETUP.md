# Complete Setup Guide

This guide will walk you through setting up the AGT Voting System from scratch.

## Prerequisites

### Required Software

1. **Python 3.9+**
   ```bash
   python --version
   ```

2. **Node.js 18+**
   ```bash
   node --version
   npm --version
   ```

3. **PostgreSQL 14+**
   - **macOS**: `brew install postgresql@14`
   - **Ubuntu/Debian**: `sudo apt install postgresql postgresql-contrib`
   - **Windows**: Download from https://www.postgresql.org/download/windows/

4. **Redis**
   - **macOS**: `brew install redis`
   - **Ubuntu/Debian**: `sudo apt install redis-server`
   - **Windows**: Download from https://github.com/microsoftarchive/redis/releases

## Step 1: Database Setup

### Start PostgreSQL

**macOS:**
```bash
brew services start postgresql@14
```

**Ubuntu/Debian:**
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Create Database

```bash
# Connect to PostgreSQL as postgres user
sudo -u postgres psql

# Or on macOS:
psql postgres

# In the PostgreSQL shell, run:
CREATE DATABASE voting_system;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE voting_system TO postgres;
\q
```

### Verify Database Connection

```bash
psql -h localhost -U postgres -d voting_system
# Enter password: postgres
# Should connect successfully
# Type \q to exit
```

## Step 2: Redis Setup

### Start Redis

**macOS:**
```bash
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo systemctl start redis
sudo systemctl enable redis
```

**Windows:**
```bash
# Run redis-server.exe from the installation directory
redis-server
```

### Verify Redis Connection

```bash
redis-cli ping
# Should return: PONG
```

## Step 3: Backend Setup

### Navigate to Backend Directory

```bash
cd /home/dev/WorkSpace/voting-system/backend
```

### Create Virtual Environment

```bash
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file with your database credentials
# Default values should work if you followed Step 1
nano .env  # or use your preferred editor
```

**.env file contents:**
```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=voting_system

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

TOKEN_EXPIRY_MINUTES=15
MAX_VOTES_PER_DEVICE=3
RATE_LIMIT_VOTES_PER_MINUTE=5
ALLOWED_CONTESTANTS=Jones,Smith,Johnson,Williams,Brown,Davis,Miller,Wilson,Moore,Taylor
```

### Initialize Database Tables

```bash
python init_db.py
```

You should see:
```
Creating database tables...
Database tables created successfully!
```

### Start Backend Server

```bash
python main.py
```

Backend should start on http://localhost:8000

**Test the backend:**
- Open http://localhost:8000 in your browser
- You should see: `{"status":"ok","service":"AGT Voting System"}`
- API docs: http://localhost:8000/docs

## Step 4: Frontend Setup

### Open New Terminal

Keep the backend running and open a new terminal window.

### Navigate to Frontend Directory

```bash
cd /home/dev/WorkSpace/voting-system/frontend
```

### Install Dependencies

```bash
npm install
```

### Start Development Server

```bash
npm run dev
```

Frontend should start on http://localhost:3000

## Step 5: Test the System

1. Open http://localhost:3000 in your browser
2. You should see the voting interface
3. Enter a contestant name (e.g., "Smith")
4. Click "Submit Vote"
5. You should see "Vote recorded for Smith!"

### Test Vote Limits

1. Vote for 2 more different contestants (e.g., "Jones", "Williams")
2. Try voting for a 4th contestant - should fail with "Maximum votes reached"
3. Try voting for "Smith" again - should fail with "You have already voted"

### Test Invalid Inputs

1. Try entering an invalid name like "InvalidName" - should fail
2. Try rapid voting - may trigger rate limiting
3. Check stats at http://localhost:8000/stats

## Troubleshooting

### Backend Issues

**"Connection refused" to PostgreSQL:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list  # macOS

# Check PostgreSQL logs
tail -f /var/log/postgresql/postgresql-14-main.log  # Linux
tail -f /usr/local/var/log/postgresql@14.log  # macOS
```

**"Connection refused" to Redis:**
```bash
# Check if Redis is running
redis-cli ping

# Start Redis if not running
sudo systemctl start redis  # Linux
brew services start redis  # macOS
```

**"Password authentication failed":**
- Update the password in .env file
- Or reset PostgreSQL password:
```bash
sudo -u postgres psql
ALTER USER postgres WITH PASSWORD 'newpassword';
\q
```

**"Database does not exist":**
```bash
sudo -u postgres psql
CREATE DATABASE voting_system;
\q
```

### Frontend Issues

**"Failed to fetch token":**
- Make sure backend is running on port 8000
- Check CORS settings in backend/main.py
- Verify network connectivity

**Token expired errors:**
- The app should auto-refresh tokens
- Try clearing localStorage and refreshing the page
- Check backend logs for errors

**npm install fails:**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Database Issues

**Reset database:**
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Drop and recreate database
DROP DATABASE voting_system;
CREATE DATABASE voting_system;
GRANT ALL PRIVILEGES ON DATABASE voting_system TO postgres;
\q

# Reinitialize tables
cd backend
python init_db.py
```

**View database contents:**
```bash
psql -h localhost -U postgres -d voting_system

# List tables
\dt

# View sessions
SELECT * FROM vote_sessions;

# View votes
SELECT * FROM votes;

# Exit
\q
```

## Development Tips

### Backend Development

**Run with auto-reload:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**View logs:**
- Backend logs appear in the terminal
- Add `import logging` for more detailed logs

**Test API with curl:**
```bash
# Get token
curl "http://localhost:8000/token?visitorId=test123&localId=uuid456"

# Submit vote
curl -X POST "http://localhost:8000/vote" \
  -H "Content-Type: application/json" \
  -H "X-Vote-Token: YOUR_TOKEN_HERE" \
  -d '{"contestant":"smith","fingerprint":"YOUR_FINGERPRINT"}'
```

### Frontend Development

**Clear browser storage:**
```javascript
// In browser console
localStorage.clear()
location.reload()
```

**View stored session:**
```javascript
// In browser console
JSON.parse(localStorage.getItem('agt_vote_session'))
```

### Database Queries

**Check vote counts:**
```sql
SELECT contestant, COUNT(*) as votes
FROM votes
GROUP BY contestant
ORDER BY votes DESC;
```

**Check suspicious sessions:**
```sql
SELECT * FROM vote_sessions WHERE is_suspicious = true;
```

**Check rate limit violations:**
```sql
SELECT ip_address, COUNT(*) as violations
FROM rate_limit_logs
GROUP BY ip_address
ORDER BY violations DESC;
```

## Next Steps

- Read [README.md](README.md) for complete documentation
- Explore API docs at http://localhost:8000/docs
- Customize contestants in backend/.env
- Deploy to production (see README for guidance)

## Quick Reference

### Services

| Service | Default URL | Check Status |
|---------|-------------|--------------|
| Backend | http://localhost:8000 | curl http://localhost:8000 |
| Frontend | http://localhost:3000 | Open in browser |
| PostgreSQL | localhost:5432 | psql -h localhost -U postgres -d voting_system |
| Redis | localhost:6379 | redis-cli ping |
| API Docs | http://localhost:8000/docs | Open in browser |

### Commands

```bash
# Start backend
cd backend && source venv/bin/activate && python main.py

# Start frontend
cd frontend && npm run dev

# Reset database
cd backend && python init_db.py

# View stats
curl http://localhost:8000/stats
```
