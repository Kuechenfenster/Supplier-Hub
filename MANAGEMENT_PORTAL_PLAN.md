# Supplier Hub - Management Portal Plan

## Overview Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Supplier Hub System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Supplier   │    │   Factory    │    │  Management  │      │
│  │    Portal    │    │    Portal    │    │    Portal    │      │
│  │              │    │              │    │              │      │
│  │ - Register   │    │ - Register   │    │ - Dashboard  │      │
│  │ - Login      │    │ - Login      │    │ - Users      │      │
│  │ - Materials  │    │ - Materials  │    │ - Depts      │      │
│  └──────┬───────┘    └──────┬───────┘    │ - Rights     │      │
│         │                   │            │ - Reports    │      │
│         │            ┌──────┴────┐       │ - Settings   │      │
│         │            │           │       └──────┬───────┘      │
│         └────────────┤  Shared   ├──────────────┘              │
│                      │ Database  │                              │
│                      │ PostgreSQL│                              │
│                      └───────────┘                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Database Schema Extensions

### New Tables Required

```sql
-- Internal Users (Company Admin/Staff)
CREATE TABLE internal_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'admin', 'manager', 'viewer'
    department_id INTEGER REFERENCES departments(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Departments
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    code VARCHAR(10) UNIQUE NOT NULL,
    description TEXT,
    manager_id INTEGER REFERENCES internal_users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Permissions/Rights
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    module VARCHAR(50) NOT NULL  -- 'suppliers', 'materials', 'reports', 'users'
);

-- Role-Permission Mapping
CREATE TABLE role_permissions (
    role VARCHAR(20) NOT NULL,
    permission_id INTEGER REFERENCES permissions(id),
    PRIMARY KEY (role, permission_id)
);

-- Audit Log
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES internal_users(id),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER,
    old_value JSONB,
    new_value JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Supplier Status Tracking
ALTER TABLE suppliers ADD COLUMN status VARCHAR(20) DEFAULT 'pending';
-- Status: pending, active, suspended, archived

ALTER TABLE suppliers ADD COLUMN assigned_to INTEGER REFERENCES internal_users(id);
ALTER TABLE suppliers ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

---

## Phase 2: Backend API Extensions

### New API Endpoints

```
# Authentication (Management Portal)
POST   /api/admin/auth/login
POST   /api/admin/auth/logout
POST   /api/admin/auth/refresh
GET    /api/admin/auth/me

# Internal Users
GET    /api/admin/users
POST   /api/admin/users
GET    /api/admin/users/{id}
PUT    /api/admin/users/{id}
DELETE /api/admin/users/{id}

# Departments
GET    /api/admin/departments
POST   /api/admin/departments
PUT    /api/admin/departments/{id}
DELETE /api/admin/departments/{id}

# Suppliers (Management View)
GET    /api/admin/suppliers           # List all with filters
GET    /api/admin/suppliers/{id}      # Detailed view
PUT    /api/admin/suppliers/{id}      # Update status, assign
DELETE /api/admin/suppliers/{id}      # Suspend/Archive

# Materials (Oversight)
GET    /api/admin/materials           # All materials across suppliers
GET    /api/admin/materials/cas-check # Validate CAS numbers

# Dashboard/Analytics
GET    /api/admin/dashboard/stats     # Counts, graphs
GET    /api/admin/dashboard/activity  # Recent activity
GET    /api/admin/dashboard/alerts    # Pending actions

# Audit
GET    /api/admin/audit               # View audit log
GET    /api/admin/audit/{user_id}     # User-specific actions

# Reports
GET    /api/admin/reports/suppliers   # Export supplier list
GET    /api/admin/reports/materials   # Export materials
GET    /api/admin/reports/compliance  # Compliance report
```

---

## Phase 3: Role-Based Access Control (RBAC)

### Default Roles

| Role | Permissions |
|------|-------------|
| **Super Admin** | Full access to all modules |
| **Department Manager** | Manage assigned suppliers, view reports, manage dept users |
| **QA Manager** | View/materials, approve formulations, compliance reports |
| **Viewer** | Read-only access to assigned data |

### Permission Matrix

| Module | Admin | Manager | QA | Viewer |
|--------|-------|---------|-----|--------|
| Users | CRUD | Read | - | - |
| Departments | CRUD | Read (own) | - | - |
| Suppliers | CRUD | CRUD (assigned) | Read | Read (assigned) |
| Materials | CRUD | Read | CRUD | Read |
| Reports | All | Dept only | Compliance | Read |
| Audit | Full | Own dept | - | - |

---

## Phase 4: Management Portal Frontend

### Pages Structure

```
/management/
├── /login                  # Admin login page
├── /dashboard              # Overview dashboard
├── /suppliers              # Supplier management
│   ├── /{id}              # Supplier details
│   └── /{id}/materials    # View supplier materials
├── /users                  # Internal user management
├── /departments            # Department management
├── /materials              # All materials overview
├── /reports                # Generate/export reports
├── /audit                  # Activity logs
└── /settings              # System settings
```

### Dashboard Widgets

1. **Quick Stats**
   - Total Suppliers
   - Active Suppliers
   - Pending Registrations
   - Total Raw Materials

2. **Charts**
   - Registrations over time
   - Suppliers by department
   - Materials by category

3. **Recent Activity**
   - New supplier registrations
   - Material additions
   - User actions

4. **Alerts/Tasks**
   - Pending approvals
   - Compliance issues
   - Suspended suppliers

---

## Phase 5: Security Implementation

### Authentication
- JWT tokens for session management
- Password hashing (bcrypt/argon2)
- Session timeout (configurable)
- Password reset via email

### Authorization
- Middleware checks permissions on each request
- Route-level protection
- API key for external integrations (optional)

### Audit Trail
- Log all admin actions
- Track data changes (before/after)
- IP address logging
- Export audit logs

---

## Phase 6: Implementation Order

### Week 1: Foundation
- [ ] Database schema migrations
- [ ] Internal users model
- [ ] Authentication system
- [ ] JWT token handling

### Week 2: Core Features
- [ ] Supplier management CRUD
- [ ] Department management
- [ ] User management
- [ ] RBAC middleware

### Week 3: Dashboard & Reports
- [ ] Dashboard statistics
- [ ] Data visualization
- [ ] Report generation
- [ ] Export functionality (PDF/CSV)

### Week 4: Polish
- [ ] Audit logging
- [ ] Email notifications
- [ ] UI/UX refinements
- [ ] Testing

---

## Phase 7: Integration Points

### Supplier Portal ↔ Management Portal

| Action | Supplier Portal | Management Portal |
|--------|-----------------|-------------------|
| Registration | Self-register | Review/Approve |
| Login | Supplier login | Admin login |
| Materials | Add/Edit | View/Validate |
| Status | View own | Update all |

### Data Flow

```
Supplier Registers → Pending Status → Admin Reviews → Active Status
                                                    ↓
                                        Assigned to Department
                                                    ↓
                                        QA Reviews Materials
                                                    ↓
                                        Compliance Verified
```

---

## Phase 8: Docker Updates

### Environment Variables

```yaml
# Add to docker-compose.yml
environment:
  # Existing
  DATABASE_URL: postgresql://supplier:supplier123@db:5432/supplier_hub
  
  # New for Management Portal
  JWT_SECRET: your-secret-key-here
  JWT_EXPIRY: 3600  # 1 hour
  ADMIN_EMAIL: admin@company.com
  ADMIN_PASSWORD: changeme  # Change after first login!
```

### Volumes (Optional Admin Data)

```yaml
volumes:
  postgres_data:
  admin_uploads:  # For reports, exports
```

---

## Technical Stack Summary

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI + SQLAlchemy |
| **Database** | PostgreSQL 15 |
| **Auth** | JWT + Password Hashing |
| **Frontend** | HTML/CSS/JavaScript (or Vue/React) |
| **Container** | Docker Compose |
| **File Storage** | Local volume / S3 (future) |

---

## Future Enhancements

1. **Two-Factor Authentication** for admin users
2. **SSO Integration** (OAuth2, SAML, LDAP)
3. **Email Notifications** for status changes
4. **API for External Systems** (ERP, CRM)
5. **Mobile App** for supplier onboarding
6. **AI Compliance Checker** for CAS validation
7. **Multi-language Support**
8. **Advanced Analytics** (PowerBI integration)

---

## Getting Started Command

```bash
# After cloning, run migration
docker compose exec web python backend/migrate.py

# Create first admin user
docker compose exec web python backend/create_admin.py

# Access management portal
http://localhost:8080/management
```
