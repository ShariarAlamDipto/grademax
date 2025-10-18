# Phase 2 Implementation Plan

## Overview

Phase 2 builds on Phase 1's foundation to add advanced session management, audit log viewing, and enhanced user experience features.

## Features Breakdown

### 🎯 Core Features (Estimated: 3-4 hours)

#### 1. Session Management UI ⭐ HIGH PRIORITY
**File:** `src/app/account/sessions/page.tsx` (new)

**Features:**
- View all active sessions for current user
- Display: Device name, Platform, Browser, IP, Last activity
- "Revoke" button for each session
- "Revoke All Other Sessions" button
- Real-time session status

**API Endpoints:**
- `GET /api/sessions` - List user's sessions
- `DELETE /api/sessions/[id]` - Revoke specific session
- `DELETE /api/sessions/revoke-all-others` - Revoke all except current

**Database:** Uses existing `user_sessions` table from Phase 1

#### 2. Admin Audit Log Viewer ⭐ HIGH PRIORITY
**File:** `src/app/admin/audit-logs/page.tsx` (new)

**Features:**
- Table view of all audit events
- Filters:
  - Event category (auth, permission, worksheet, admin, security)
  - Event type dropdown
  - User search/filter
  - Date range picker
  - Status filter (success/failure/error)
- Pagination (50 events per page)
- Export to CSV
- Hash chain integrity checker UI

**Components:**
- `AuditLogTable` - Main table with sorting
- `AuditLogFilters` - Filter controls
- `AuditLogDetails` - Expandable row details
- `IntegrityStatus` - Shows hash chain status

**API Endpoints:**
- `GET /api/admin/audit-logs` - Get paginated logs with filters
- `GET /api/admin/audit-logs/verify` - Verify hash chain integrity
- `GET /api/admin/audit-logs/export` - Export to CSV

#### 3. Recent Worksheets Component ⭐ MEDIUM PRIORITY
**File:** `src/components/dashboard/RecentWorksheets.tsx` (new)

**Features:**
- Shows last 10 worksheets generated
- Display: Subject, Topics, Date, Questions count, Status
- "Download PDF" button
- "Generate Similar" quick action
- Empty state with CTA

**Integration:** Add to existing dashboard

### 🔧 Enhancement Features (Estimated: 2-3 hours)

#### 4. Trusted Devices Management
**File:** `src/app/account/devices/page.tsx` (new)

**Features:**
- List of devices that have accessed account
- Mark devices as "trusted"
- Remove devices
- See first/last seen dates

#### 5. Usage Analytics Dashboard
**File:** `src/app/admin/analytics/page.tsx` (new)

**Features:**
- Total users count
- Active users (last 7 days)
- Worksheets generated (daily/weekly/monthly charts)
- Most popular subjects/topics
- Quota usage overview
- Growth trends

**Charts:** Use Recharts or Chart.js

### 🎨 UX Enhancements (Estimated: 1-2 hours)

#### 6. Improved Dashboard
**Updates to:** `src/app/dashboard/page.tsx`

**Add:**
- Welcome message with tips
- Recent activity timeline
- Quick stats cards with icons
- "What's New" section
- Keyboard shortcuts hint

#### 7. Notification System
**File:** `src/components/NotificationCenter.tsx` (new)

**Features:**
- Bell icon in header
- Dropdown with recent notifications
- Types: Permission granted, Quota warning, System updates
- Mark as read functionality

### 🔐 Advanced Auth Features (Optional - Estimated: 6-8 hours)

#### 8. WebAuthn/Passkeys Support
**Files:**
- `src/lib/webauthn.ts` - WebAuthn helper
- `src/app/account/passkeys/page.tsx` - Passkey management
- Migration for passkey storage

**Features:**
- Register passkeys
- Authenticate with passkeys
- Fallback to Google OAuth
- Manage multiple passkeys

**Note:** Complex feature, requires:
- Browser compatibility checks
- Fallback mechanisms
- Secure challenge generation
- Device attestation

#### 9. Magic Link Authentication
**Files:**
- `src/app/api/auth/magic-link/route.ts`
- Email templates

**Features:**
- Passwordless login via email
- Time-limited tokens (15 min)
- One-time use links
- Email template styling

## Implementation Order (Recommended)

### Sprint 1: Session & Audit (1 session, ~3 hours)
1. Session Management UI ✅
2. Admin Audit Log Viewer ✅
3. Recent Worksheets Component ✅

### Sprint 2: Devices & Analytics (1 session, ~2 hours)
4. Trusted Devices Management ✅
5. Usage Analytics Dashboard ✅

### Sprint 3: UX Polish (1 session, ~2 hours)
6. Improved Dashboard ✅
7. Notification System ✅

### Sprint 4: Advanced Auth (Optional, 2-3 sessions)
8. WebAuthn/Passkeys ⚠️ Complex
9. Magic Link Auth ⚠️ Requires email

## Code Structure

```
src/
├── app/
│   ├── account/
│   │   ├── sessions/page.tsx          # Session management
│   │   ├── devices/page.tsx           # Device management
│   │   └── passkeys/page.tsx          # Passkey management
│   ├── admin/
│   │   ├── audit-logs/page.tsx        # Audit log viewer
│   │   └── analytics/page.tsx         # Analytics dashboard
│   └── api/
│       ├── sessions/
│       │   ├── route.ts               # List sessions
│       │   ├── [id]/route.ts          # Revoke session
│       │   └── revoke-all/route.ts    # Revoke all others
│       └── admin/
│           ├── audit-logs/route.ts    # Get logs
│           └── audit-logs/export/route.ts  # Export CSV
├── components/
│   ├── dashboard/
│   │   └── RecentWorksheets.tsx       # Recent worksheets
│   ├── admin/
│   │   ├── AuditLogTable.tsx          # Audit log table
│   │   ├── AuditLogFilters.tsx        # Filters
│   │   └── AnalyticsCharts.tsx        # Charts
│   └── NotificationCenter.tsx         # Notifications
└── lib/
    ├── webauthn.ts                    # WebAuthn helpers
    └── sessionManager.ts              # Session utilities
```

## Database Changes

No new migrations needed! Phase 1 tables support all Phase 2 features:
- ✅ `user_sessions` - For session management
- ✅ `trusted_devices` - For device management
- ✅ `audit_log` - For audit viewer
- ✅ `usage_meters` - For analytics

## Testing Checklist

### Session Management
- [ ] View active sessions
- [ ] Revoke a session
- [ ] Revoke all others
- [ ] Session expires automatically
- [ ] Can't revoke current session without warning

### Audit Logs
- [ ] View all logs
- [ ] Filter by category
- [ ] Filter by user
- [ ] Filter by date range
- [ ] Export to CSV
- [ ] Verify hash chain integrity
- [ ] Pagination works

### Recent Worksheets
- [ ] Shows last 10 worksheets
- [ ] Download PDF works
- [ ] Empty state displays
- [ ] "Generate Similar" creates new worksheet with same settings

### Analytics
- [ ] Charts render correctly
- [ ] Data updates in real-time
- [ ] Filters work
- [ ] Mobile responsive

## Dependencies Needed

```bash
# If adding charts
npm install recharts

# If adding date picker for filters
npm install react-datepicker @types/react-datepicker

# If adding WebAuthn
npm install @simplewebauthn/server @simplewebauthn/browser
```

## API Response Examples

### GET /api/sessions
```json
{
  "sessions": [
    {
      "id": "uuid",
      "device_label": "Chrome on Windows",
      "platform": "web",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "is_active": true,
      "is_current": true,
      "last_activity_at": "2025-10-19T10:30:00Z",
      "created_at": "2025-10-19T09:00:00Z",
      "expires_at": "2025-10-20T09:00:00Z"
    }
  ]
}
```

### GET /api/admin/audit-logs?category=permission&page=1
```json
{
  "logs": [...],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 250,
    "total_pages": 5
  },
  "integrity": {
    "valid": true,
    "last_verified": "2025-10-19T10:30:00Z"
  }
}
```

## Deployment Notes

- No breaking changes
- All features are additive
- Existing users unaffected
- Can deploy incrementally (feature by feature)
- Backward compatible with Phase 1

## Estimated Time

- **Core Features (1-3):** 3-4 hours
- **Enhancement Features (4-5):** 2-3 hours
- **UX Polish (6-7):** 1-2 hours
- **Advanced Auth (8-9):** 6-8 hours (optional)

**Total:** 6-9 hours for essential features, 12-17 hours for complete Phase 2

## Decision Points

**Question 1:** Do we want WebAuthn/Passkeys now?
- ✅ Yes → Add to Sprint 4 (complex, takes time)
- ❌ No → Skip for now, can add later

**Question 2:** Do we need email capabilities?
- ✅ Yes → Can add Magic Links
- ❌ No → Stick with Google OAuth only

**Question 3:** Analytics depth?
- 📊 Full dashboard with charts → Takes longer
- 📝 Simple stats cards → Faster

---

## Let's Start! 🚀

**Recommendation:** Start with Sprint 1 (Session Management + Audit Viewer + Recent Worksheets)

These are the most valuable features that enhance security and UX without requiring complex setup.

**Ready to begin?** Let me know which features you want first!
