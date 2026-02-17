# KPS Flask — Logistics & Parcel Management

A web-based logistics management system for tracking parcel shipments, managing vendors, generating invoices, and monitoring business analytics.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.1-green)
![SQLite](https://img.shields.io/badge/Database-SQLite-orange)

## Features

- **Entry Management** — Add, edit, and delete parcel shipment entries with vendor-specific charge columns
- **Multi-Vendor Support** — Manage vendors with custom rates, billing info, and configurable column visibility
- **Invoice Generation** — Generate printable bills per vendor/month with pending balance support
- **Analytics Dashboard** — KPI cards, revenue trends, vendor share pie charts, and daily activity tracking
- **User Management** — Role-based access (Admin / Staff) with account enable/disable
- **Audit Logging** — Tracks all user actions (logins, CRUD operations, invoice generation)
- **System Admin Panel** — Server health monitoring, DB optimization (VACUUM), backup download, and log cleanup
- **Chat Command Interface** — Natural language queries for quick revenue checks, vendor lookups, and balance updates
x
## Tech Stack

| Layer       | Technology         |
|-------------|-------------------|
| Backend     | Flask 3.1, Python  |
| Database    | SQLite + SQLAlchemy |
| Auth        | Flask-Login        |
| Templates   | Jinja2             |
| Monitoring  | psutil             |

## Getting Started

### Prerequisites

- Python 3.10+

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd kps-flask

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the App

```bash
python run.py
```

The app starts at **http://127.0.0.1:5000** with debug mode enabled.

### Default Login

| Username | Password   | Role  |
|----------|-----------|-------|
| `admin`  | `admin123` | Admin |

> A default admin account is auto-created on first run if no users exist in the database.

## Project Structure

```
kps-flask/
├── run.py                    # Application entry point
├── requirements.txt          # Python dependencies
├── instance/
│   └── logistics.db          # SQLite database (auto-created)
└── app/
    ├── __init__.py           # App factory (create_app)
    ├── extensions.py         # Flask extensions (db, login_manager)
    ├── models.py             # SQLAlchemy models
    ├── routes/
    │   ├── auth.py           # Login / Logout
    │   ├── core.py           # Entry CRUD, dashboard
    │   ├── reports.py        # Invoices & analytics
    │   ├── chat.py           # Chat command API
    │   └── admin/
    │       ├── __init__.py   # Admin blueprint
    │       ├── dashboard.py  # Settings page & system stats
    │       ├── users.py      # User management
    │       ├── vendors.py    # Vendor management
    │       └── system.py     # DB optimize, backup, log cleanup
    ├── templates/            # Jinja2 HTML templates
    └── static/               # Static assets (images)
```

## Data Models

| Model      | Purpose                                        |
|------------|------------------------------------------------|
| `User`     | Authentication with admin/staff roles          |
| `Vendor`   | Vendor profiles, rates, billing info, column toggles |
| `Entry`    | Individual parcel shipment records             |
| `AuditLog` | Timestamped activity log for all user actions  |

## API Endpoints

| Method | Route                           | Description              |
|--------|--------------------------------|--------------------------|
| GET/POST | `/`, `/home`                 | Dashboard + add entry    |
| GET    | `/view`                        | View entries (filterable)|
| GET    | `/edit/<id>`                   | Edit an entry            |
| GET    | `/invoices`                    | Invoice selection page   |
| GET    | `/generate_bill`               | Generate printable invoice|
| GET    | `/analytics`                   | Analytics dashboard      |
| GET    | `/settings`                    | Admin settings panel     |
| POST   | `/api/chat`                    | Chat command interface   |

## License

This project is private and not licensed for public distribution.
