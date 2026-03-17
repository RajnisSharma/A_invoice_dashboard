# A_invoice_dashboard

A full-stack invoice dashboard with a Django REST API backend and a React frontend. The backend stores real invoice data (vendors, airlines, invoices, line items) and exposes CRUD endpoints with filters, summaries, and rule-based signals. The frontend provides a modern dashboard view with KPIs, filters, AI signals, and live flagging.

**Features**
- Real database-backed invoices, vendors, airlines, and line items.
- CRUD APIs with search, filters, and optional pagination.
- Airline summary totals and invoice counts.
- Rule-based AI signals (high value, overdue, missing GSTIN, flagged).
- Modern UI dashboard with KPIs, filters, and in-place flagging.

**Tech Stack**
- Django + Django REST Framework
- React (Create React App)
- Bootstrap 5 (base dependency)
- SQLite (default DB)

**Project Structure**
- `invoice_dashboard/` Django project (backend)
- `invoice_dashboard/invoice_app/` API, models, serializers
- `invoice_dashboard/invoice-frontend/` React app (frontend)

**Quick Start**
Backend (Django)
1. `cd invoice_dashboard`
1. Optional: create and activate a virtual environment.
1. `pip install -r requirement.txt`
1. `python manage.py migrate`
1. `python manage.py seed_demo --reset`
1. `python manage.py runserver`

API base: `http://localhost:8000/api`

Frontend (React)
1. `cd invoice_dashboard/invoice-frontend`
1. `npm install`
1. `npm start`

UI: `http://localhost:3000`

**Environment Variable**
The frontend reads the API base from `REACT_APP_API_BASE`.
If not set, it defaults to `http://localhost:8000/api`.

Example (PowerShell):
```powershell
$env:REACT_APP_API_BASE="http://localhost:8000/api"
npm start
```

**API Endpoints**
- `GET /api/invoices/` List invoices
- `POST /api/invoices/` Create invoice (with optional line items)
- `GET /api/invoices/{id}/` Retrieve invoice
- `PATCH /api/invoices/{id}/` Update invoice (for flagging, status, etc.)
- `DELETE /api/invoices/{id}/` Delete invoice
- `GET /api/summary/` Airline totals and invoice counts
- `GET /api/ai-suggest/` Rule-based signals
- `GET /api/vendors/` Vendors CRUD
- `GET /api/airlines/` Airlines CRUD
- `GET /api/invoice-lines/` Line items CRUD

**Filtering and Search**
Invoice list supports:
- `status`, `vendor`, `airline`, `invoice_no`
- `date_from`, `date_to`, `due_from`, `due_to`
- `min_total`, `max_total`
- `overdue=true`, `flagged=true`
- `q` (free text search)

Pagination is optional. Add `?page=1` or `?page_size=20` to enable paginated responses.

**Demo Data**
Seed 5 demo invoices with vendors, airlines, and line items:
```powershell
cd invoice_dashboard
python manage.py seed_demo --reset
```

**Tests**
Run backend tests:
```powershell
cd invoice_dashboard
python manage.py test invoice_app
```

**Notes**
- Invoice totals are calculated from line items.
- Flags are persisted to the backend via `PATCH /api/invoices/{id}/`.
