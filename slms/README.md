# Smart Library Management System — Python/Flask

## How to Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the server
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

## Test Accounts
| Username | Password | Role |
|---|---|---|
| admin | admin123 | Librarian |
| staff1 | staff123 | Staff |
| student1 | student123 | Student |
| teacher1 | teacher123 | Teacher |

## Project Structure
```
slms/
├── app.py              ← Flask backend (all routes & logic)
├── requirements.txt    ← Python dependencies
├── templates/
│   ├── login.html      ← Login & register page
│   └── app.html        ← Main application (all views)
└── static/
    └── css/
        └── style.css   ← All styles
```

## Features
- Role-based dashboards (Librarian, Staff, Student, Teacher)
- Book management (add, edit, archive)
- Borrow requests & approvals
- Reservation system
- Penalty tracking & clearance
- Data analytics dashboard (category charts, top books, weekly activity)
- AI chatbot (powered by Claude API)
- User management
