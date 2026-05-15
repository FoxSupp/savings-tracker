# Savings Tracker — SPEC.md

## 1. Concept & Vision

A lightweight personal savings tracker to log and categorize savings across financial accounts (Bar cash, Trade Republic, ETF, Tagesgeld, Aktien, Krypto, Other). Single-page dashboard shows totals and recent entries. Designed for quick local use via browser inside an LXC container.

## 2. Tech Stack

- **Backend**: Flask (Python 3)
- **Database**: SQLite (single file, auto-created)
- **Frontend**: Jinja2 templates (vanilla HTML/CSS, minimal JS)
- **Deployment**: Docker + docker-compose targeting LXC 100 (x86_64, privileged mode)

## 3. Data Model

**Table: `savings`**

| Column    | Type     | Constraints               |
|-----------|----------|---------------------------|
| id        | INTEGER  | PRIMARY KEY AUTOINCREMENT |
| category  | TEXT     | NOT NULL                  |
| amount    | REAL     | NOT NULL                  |
| date      | TEXT     | NOT NULL (YYYY-MM-DD)     |
| notes     | TEXT     | NULLABLE                  |
| created_at| TEXT     | NOT NULL                  |

**Categories**: `Bar`, `Trade Republic`, `ETF`, `Tagesgeld`, `Aktien`, `Krypto`, `Other`

## 4. Features & Endpoints

### Web UI (Browser)

| Route        | Method | Description                              |
|--------------|--------|------------------------------------------|
| `/`          | GET    | Dashboard: totals by category + entry list |
| `/add`       | GET    | Show add-entry form                      |
| `/add`       | POST   | Handle form submit → create entry        |
| `/edit/<id>` | GET    | Show edit-entry form pre-filled          |
| `/edit/<id>` | POST   | Handle form submit → update entry        |
| `/delete/<id>`| POST  | Delete entry → redirect to `/`           |

### API (optional JSON)

| Route     | Method | Description                     |
|-----------|--------|---------------------------------|
| `/api/entries` | GET | List all entries (JSON)         |
| `/api/entries` | POST | Create entry (JSON)            |
| `/api/entries/<id>` | PUT | Update entry (JSON)        |
| `/api/entries/<id>` | DELETE | Delete entry (JSON)     |

## 5. Dashboard View

- **Header**: App title "Savings Tracker"
- **Summary Cards**: One card per category showing total amount saved
- **Grand Total**: Sum across all categories
- **Entry Table**: Columns — Date, Category, Amount, Notes, Actions (Edit, Delete)
- **Add Entry Button**: Links to `/add`

## 6. Forms

### Add / Edit Entry

- **Category**: `<select>` dropdown with all 7 categories
- **Amount**: `<input type="number" step="0.01">`
- **Date**: `<input type="date">` (defaults to today)
- **Notes**: `<textarea>` optional

Validation: category and amount (must be > 0) and date required.

## 7. Docker Setup

### Dockerfile (python:3.11-slim)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
```

### docker-compose.yml

```yaml
version: "3.8"
services:
  app:
    build: .
    container_name: savings-tracker
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data        # persist SQLite file
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### LXC 100 Notes

- Image: `docker.io/library/python:3.11-slim`
- Privileged mode required for Docker-in-Docker if needed
- Port `5000` exposed to host or reverse-proxy

## 8. File Structure

```
savings-tracker/
├── SPEC.md
├── app.py              # Single-file Flask application
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── data/               # SQLite DB created at runtime
    └── savings.db
```

## 9. Acceptance Criteria

1. Dashboard displays all categories with correct totals
2. Can add a new savings entry with all fields
3. Can edit an existing entry
4. Can delete an entry
5. SQLite database persists between restarts (via volume mount)
6. Docker build completes without error
7. Docker-compose up starts the container and the app responds on port 5000
8. App runs inside an LXC 100 container (x86_64)
