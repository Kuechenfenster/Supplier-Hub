# Supplier Hub

A comprehensive supplier management system for cosmetic raw materials compliance and product formulation.

## 🏗 Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────────┐
│   Supplier  │    │   Factory   │    │   Management    │
│   Portal    │    │   Portal    │    │   Portal        │
│             │    │             │    │   (Admin)       │
└──────┬──────┘    └──────┬──────┘    └────────┬────────┘
       │                  │                     │
       └──────────────────┼─────────────────────┘
                          │
                   ┌──────▼──────┐
                   │  PostgreSQL │
                   │   Database  │
                   └─────────────┘
```

## 🚀 Quick Deployment

### On Docker-enabled server:

```bash
# Clone repository
git clone https://github.com/Kuechenfenster/Supplier-Hub.git
cd Supplier-Hub

# Start with Docker Compose
docker compose up -d --build

# View logs
docker compose logs -f
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Supplier Portal** | http://localhost:8080 | Factory/supplier registration |
| **Management Portal** | http://localhost:8080/management | Admin dashboard |
| **Management Login** | http://localhost:8080/management/login | Admin login |
| **PostgreSQL** | localhost:5432 | Database (internal) |

## 🔐 First-Time Setup

### 1. Get Admin Invitation Code

```bash
# View initialization logs
docker compose logs web | grep "Invitation Code"
```

Or check the database directly:
```bash
docker compose exec db psql -U supplier -d supplier_hub -c "SELECT username, invitation_code FROM internal_users WHERE username='admin';"
```

### 2. Accept Invitation

1. Go to `http://localhost:8080/management/login`
2. Click "Accept Invitation" link
3. Enter invitation code
4. Set your admin password
5. Login with username `admin`

### 3. Create Additional Users

1. Login to Management Portal
2. Go to **Users** tab
3. Click **+ Add User**
4. Fill in user details
5. Send the generated invitation code to the user
6. User accepts invitation and sets password

## 👥 User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full system access, user management, password resets |
| **Manager** | Manage assigned suppliers, view team data |
| **QA** | Materials compliance, formulation approval |
| **Viewer** | Read-only access to assigned data |

## 🔧 Configuration

### Environment Variables

```yaml
# docker-compose.yml
services:
  web:
    environment:
      DATABASE_URL: postgresql://supplier:supplier123@db:5432/supplier_hub
      JWT_SECRET: change-this-secret-in-production
      JWT_EXPIRY: "3600"  # Token expiry in seconds
```

### Default Credentials

| Component | Username | Password |
|-----------|----------|----------|
| PostgreSQL | supplier | supplier123 |
| Admin User | admin | (set via invitation) |

## 📊 Management Portal Features

### Dashboard
- Total suppliers, active/pending counts
- Active users and departments
- Recent activity feed

### User Management
- Create users with invitation codes
- Assign roles (Admin/Manager/QA/Viewer)
- Assign departments
- Activate/deactivate users (soft delete)
- Reset passwords (Admin only)

### Department Management
- Create organizational departments
- Assign users to departments
- Department-based access control

### Supplier Overview
- View all registered suppliers
- Filter by status (pending/active/suspended)
- Assign suppliers to managers

### Audit Log
- Complete activity history
- User actions tracking
- Entity change logs

## 🔒 Security Features

- **Invitation-only registration** - Users can only join via invitation code
- **Password hashing** - bcrypt for all passwords
- **JWT authentication** - Secure token-based auth
- **Soft delete** - Deactivated users hidden but records preserved
- **Audit logging** - All admin actions tracked
- **Session expiry** - Configurable token lifetime

## 📁 Project Structure

```
Supplier-Hub/
├── backend/
│   ├── main.py          # FastAPI application
│   ├── models.py        # SQLAlchemy database models
│   ├── init_db.py       # Database initialization
│   ├── migrate.py       # Database migrations
│   └── requirements.txt # Python dependencies
├── static/
│   ├── management.html         # Management portal UI
│   ├── management-login.html   # Admin login page
│   └── assets/
│       └── logo.png    # Company logo
├── index.html           # Supplier registration portal
├── Dockerfile           # Web application container
├── docker-compose.yml   # Service orchestration
└── README.md           # This file
```

## 🔧 Useful Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f web
docker compose logs -f db

# Restart services
docker compose restart

# Rebuild after code changes
docker compose up -d --build

# Access database
docker compose exec db psql -U supplier -d supplier_hub

# Reset everything (WARNING: deletes all data!)
docker compose down -v
docker compose up -d --build
```

## 🔄 Updating

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker compose up -d --build
```

## 🚨 Troubleshooting

### Docker daemon not running
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

### Port already in use
```bash
# Change port in docker-compose.yml
ports:
  - "8090:8080"  # Use 8090 instead of 8080
```

### Database connection errors
```bash
# Check if database is healthy
docker compose ps

# Wait for health check to pass
docker compose logs db | grep "ready to accept connections"
```

### Lost admin access
```bash
# Reset admin invitation
docker compose exec db psql -U supplier -d supplier_hub -c "UPDATE internal_users SET invitation_used=false, invitation_code='NEWCODE123' WHERE username='admin';"
```

## 📝 License

Proprietary - HTI Internal Use

## 🤝 Support

For issues or questions, contact the development team.
