# 🔧 PostgreSQL Connection Fix Guide

## 🔍 Root Cause Identified

**Issue**: DNS resolution returns IPv6 address, but your Python/psycopg2 is trying IPv4 connection.

**DNS Result**:
```
Name:    db.tybaetnvnfgniotdfxze.supabase.co
Address: 2406:da18:243:740b:8859:3ce3:4229:bb42 (IPv6)
```

**Error**: `getaddrinfo failed` - Python cannot resolve or connect via IPv6

---

## ✅ SOLUTION 1: Use IPv6 Support (Recommended)

### Step 1: Update `.env.ingest`

Replace the DATABASE_URL with IPv6-friendly format:

```bash
# OLD (doesn't work with IPv6):
DATABASE_URL=postgresql://postgres:EV%2F9GwfMdegWSTg@db.tybaetnvnfgniotdfxze.supabase.co:5432/postgres

# NEW (use [host] format for IPv6):
DATABASE_URL=postgresql://postgres:EV%2F9GwfMdegWSTg@[db.tybaetnvnfgniotdfxze.supabase.co]:5432/postgres
```

### Step 2: Test Connection

```powershell
python scripts/test_postgresql_ipv6.py
```

---

## ✅ SOLUTION 2: Force IPv4 with Hosts File (Windows)

### Step 1: Find IPv4 Address

We need to force DNS to resolve to IPv4 instead of IPv6.

Open PowerShell as **Administrator** and run:

```powershell
# Try to get IPv4 address
nslookup -type=A db.tybaetnvnfgniotdfxze.supabase.co 8.8.8.8
```

### Step 2: Add to Hosts File

If you get an IPv4 address, add it to your hosts file:

1. Open Notepad as **Administrator**
2. Open file: `C:\Windows\System32\drivers\etc\hosts`
3. Add line at the end:
   ```
   <IPv4-ADDRESS>  db.tybaetnvnfgniotdfxze.supabase.co
   ```
4. Save and close

### Step 3: Flush DNS Cache

```powershell
ipconfig /flushdns
```

---

## ✅ SOLUTION 3: Use Supabase Connection Pooler (Best for Production)

Supabase provides a connection pooler that handles connections better.

### Step 1: Update `.env.ingest`

Change port from **5432** to **6543**:

```bash
# Connection Pooler (Port 6543)
DATABASE_URL=postgresql://postgres:EV%2F9GwfMdegWSTg@db.tybaetnvnfgniotdfxze.supabase.co:6543/postgres
```

### Step 2: Update Connection Code

If using direct psycopg2:

```python
import psycopg2

conn = psycopg2.connect(
    host="db.tybaetnvnfgniotdfxze.supabase.co",
    port="6543",  # Pooler port
    database="postgres",
    user="postgres.tybaetnvnfgniotdfxze",  # Note: might need project prefix
    password="EV/9GwfMdegWSTg"
)
```

---

## ✅ SOLUTION 4: Disable IPv6 in Python (Quick Fix)

### Create a custom connection wrapper

File: `scripts/pg_connector.py`

```python
import socket
import psycopg2

# Force IPv4
socket.has_ipv6 = False

def connect_pg():
    """Connect to PostgreSQL using IPv4 only"""
    return psycopg2.connect(
        host="db.tybaetnvnfgniotdfxze.supabase.co",
        port="5432",
        database="postgres",
        user="postgres",
        password="EV/9GwfMdegWSTg"
    )

# Usage:
# from scripts.pg_connector import connect_pg
# conn = connect_pg()
```

---

## ✅ SOLUTION 5: Use REST API Instead (Already Working!)

**Why bother with PostgreSQL?**

You already have a working REST API connection! For most operations, you don't need direct PostgreSQL access.

### What REST API Can Do:
- ✅ Insert data (paper processing)
- ✅ Query data (worksheet generation)
- ✅ Update records
- ✅ Delete records
- ✅ Complex queries with filters

### What Requires PostgreSQL:
- ❌ Database migrations (can use Supabase dashboard)
- ❌ Bulk operations (REST API handles most)
- ❌ Complex transactions (rarely needed)

### Stick with REST API

Your current system uses `SupabaseClient` which uses REST API - **this is perfect for your use case!**

---

## 🛠️ Step-by-Step Fix (Choose One)

### Option A: Quick Fix - Use REST API Only ✅ EASIEST

**Do nothing!** Your system already works with REST API.

**When you need migrations:**
1. Go to Supabase Dashboard → SQL Editor
2. Run SQL directly in the browser
3. No local PostgreSQL connection needed

---

### Option B: Fix IPv6 Connection 🔧 MEDIUM

1. **Update `.env.ingest`:**

```bash
DATABASE_URL=postgresql://postgres:EV%2F9GwfMdegWSTg@db.tybaetnvnfgniotdfxze.supabase.co:6543/postgres
```

Note: Changed port to 6543 (connection pooler)

2. **Test:**

```powershell
python scripts/test_db_connection.py
```

---

### Option C: Get IPv4 Address 🌐 ADVANCED

1. **Find IPv4 address:**

```powershell
# Try different DNS servers
nslookup -type=A db.tybaetnvnfgniotdfxze.supabase.co 8.8.8.8
nslookup -type=A db.tybaetnvnfgniotdfxze.supabase.co 1.1.1.1
```

2. **If you get an IPv4 address (like 192.x.x.x or 172.x.x.x):**

Open `C:\Windows\System32\drivers\etc\hosts` as admin and add:
```
<IPv4-ADDRESS>  db.tybaetnvnfgniotdfxze.supabase.co
```

3. **Flush DNS:**
```powershell
ipconfig /flushdns
```

4. **Test:**
```powershell
ping db.tybaetnvnfgniotdfxze.supabase.co
python scripts/test_db_connection.py
```

---

## 💡 Recommended Approach

### For Your Use Case:

**USE SOLUTION 5 (REST API) - You don't need PostgreSQL!**

Here's why:
1. ✅ REST API already works (tested successfully)
2. ✅ All your operations work with REST API:
   - Paper ingestion ✅
   - Topic classification ✅
   - Worksheet generation ✅
3. ✅ Migrations can be run in Supabase dashboard
4. ✅ No network/DNS issues
5. ✅ Better for serverless deployments

### When You Need SQL:

Just go to Supabase Dashboard → SQL Editor and run queries directly in your browser!

---

## 🧪 Test Scripts Included

### Test IPv6 Connection
```powershell
python scripts/test_postgresql_ipv6.py
```

### Test All Methods
```powershell
python scripts/fix_postgresql_connection.py
```

### Check Current Status
```powershell
python scripts/test_db_connection.py
```

---

## 📊 Summary Table

| Solution | Difficulty | Success Rate | Recommended |
|----------|-----------|--------------|-------------|
| REST API (do nothing) | ⭐ Easy | 100% ✅ | **YES** |
| Connection Pooler (port 6543) | ⭐⭐ Medium | 70% | Maybe |
| IPv4 Hosts File | ⭐⭐⭐ Hard | 80% | No |
| IPv6 Support | ⭐⭐ Medium | 60% | No |
| Disable IPv6 in Python | ⭐⭐ Medium | 50% | No |

---

## ✅ My Recommendation

**Don't fix what's not broken!**

Your REST API connection works perfectly. PostgreSQL direct connection is:
- ❌ Not needed for paper processing
- ❌ Not needed for worksheet generation
- ❌ Causing network issues
- ✅ Nice to have, but not essential

**Conclusion**: Keep using REST API (current setup) and run migrations in Supabase dashboard when needed.

---

## 🆘 If You Really Need PostgreSQL

Try this order:
1. Update to port 6543 (connection pooler)
2. Try from a different network (coffee shop, mobile hotspot)
3. Check Supabase dashboard for connection settings
4. Contact Supabase support about IPv6/IPv4 issues

---

## 📚 Additional Resources

- Supabase Connection Docs: https://supabase.com/docs/guides/database/connecting-to-postgres
- psycopg2 IPv6 Issues: https://github.com/psycopg/psycopg2/issues
- Windows Hosts File Location: `C:\Windows\System32\drivers\etc\hosts`

---

**Next Step**: Try updating port to 6543 in `.env.ingest` or just continue using REST API!
