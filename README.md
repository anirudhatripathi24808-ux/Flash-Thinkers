# FLASHNOVA – Futuristic Next-Gen EdTech Platform
> **"Every Student Matters. Every Confusion Counts."**

**FLASHNOVA** is a full-stack, futuristic educational platform engineered for real-time classroom intelligence, anonymous student confusion tracking, cryptographic dynamic QR attendance, and privacy-guaranteed analytics.

*GitHub Repository:* [https://github.com/anirudhatripathi24808-ux/Flash-Thinkers](https://github.com/anirudhatripathi24808-ux/Flash-Thinkers)  
*Expected Frontend URL (GitHub Pages):* [https://anirudhatripathi24808-ux.github.io/Flash-Thinkers/](https://anirudhatripathi24808-ux.github.io/Flash-Thinkers/)  
*Default Backend Deployment Service:* [https://flashnova-backend.onrender.com](https://flashnova-backend.onrender.com)  

---

## 🌟 Core Architectural Pillars

### 1. Dynamic 10-Second Rotating Cryptographic QR
- QR code refreshes every **10 seconds** with cryptographically secure random tokens.
- Visual circular countdown timer on the teacher's dashboard.
- Anti-replay and expiration protection validated strictly on the backend.
- Prevents screenshot sharing across offsite chats.
- Configurable **QR Auto-Enrollment**: When enabled, registered students scanning the active QR code are automatically enrolled in the classroom.

### 2. Triple-Button Real-Time Understanding Radar
Student dashboard features three distinct interactive feedback buttons:
- **`I UNDERSTAND`** (Neon Cyan / Emerald) – Concept is clear and pace is optimal.
- **`I HAVE A DOUBT`** (Amber / Yellow) – Concept requires quick clarification.
- **`I DON'T UNDERSTAND`** (Coral / Red) – Concept is confusing / needs repetition.
- **100% Anonymous by Default:** Identity is never tied to understanding responses. Teachers see real-time doughnut distribution and topic confusion charts.

### 3. Voluntary Doubt Channel with Explicit Consent
- Students can click **"VOLUNTEER TO ASK A DOUBT"** to submit a written question directly to the teacher's inbox.
- **Strict Privacy Rule:** Clicking *I Have a Doubt* or *I Don't Understand* never reveals identity. Only an explicit confirmation checkbox in the volunteer dialog authorizes disclosing the student's Full Name and Enrollment Number to the authorized teacher for that single request.
- Every disclosure is logged to an internal `AuditEvent` table.
- Teachers can reply with guidance and update doubt status (`Pending`, `In Progress`, `Resolved`).

### 4. Strict Privacy & Masked 10-Digit Enrollment Numbers
- Teachers **NEVER** see student names, emails, internal user IDs, or unmasked enrollment numbers in:
  - Teacher Dashboard
  - Attendance Records
  - Question-Answer Submissions
  - Analytics API endpoints & Socket.IO streams
  - CSV Exports & PDF Reports
- **10-Digit Rule:** Numbers are formatted as `1234******` (first 4 digits visible, 6 asterisks).
- **Collision Aliasing:** If multiple students share the same first 4 digits, an alias suffix is automatically added (e.g., `1234****** (#1)`, `1234****** (#2)`).
- Filtering is executed strictly in the backend before JSON/CSV/PDF serialization.

### 5. Automated Question-Driven Attendance Engine
A student is marked **`Present`** ONLY when:
1. They scan a valid active QR token for the lecture.
2. Required presence verification is completed/approved.
3. They attempt **every compulsory question** assigned to that lecture (correctness does not affect attendance; missing even one compulsory question leaves the status as **`In Progress`**).
- Statuses: `Present`, `In Progress`, `Pending Verification`, `Not Marked`.

### 6. Post-Class Reports (CSV & PDF)
- Instant export of post-class summary after teacher ends a lecture.
- Formats: High-fidelity PDF with tables and styled CSV spreadsheets.
- Both formats strictly maintain the masked enrollment privacy guarantee.

---

## 🛠 Technology Stack

- **Frontend:** HTML5, CSS3, ES6+ JavaScript, Chart.js, QRCode.js, Font Awesome 6.
  - *Theme:* Deep Midnight Navy (`#060913`), Neon Cyan (`#00f2fe`), Electric Violet (`#8b5cf6`).
  - *Design:* Glassmorphism panels, glowing borders, responsive mobile/desktop layouts.
- **Backend:** Python Flask 3.1+, Flask-SocketIO 5.3+, SQLAlchemy 2.0+, Werkzeug security hashing.
- **Database:** SQLite for local development (`backend/flashnova.db`), PostgreSQL-ready architecture for Render/production.
- **Real-Time:** WebSockets for live QR rotation, confusion radar tally, and doubt alerts.
- **Report Generation:** Python ReportLab (PDF) and native CSV streaming.

---

## 🚀 Local Development Setup

### Prerequisites
- Python 3.11+ (or 3.14)
- Git

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/anirudhatripathi24808-ux/Flash-Thinkers.git
cd Flash-Thinkers

pip install -r backend/requirements.txt
```

### 2. Environment Configuration
Copy the example environment file:
```bash
cp .env.example .env
```
Default Subject Access Codes:
- Mathematics: `MAT121`
- Chemistry: `CHM131`
- Workshop: `WSP111`

### 3. Run the Unified Server
```bash
python run.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser:
- **Landing Page:** [http://localhost:5000/](http://localhost:5000/)
- **Student Portal:** [http://localhost:5000/student.html](http://localhost:5000/student.html)
- **Teacher Hub:** [http://localhost:5000/teacher.html](http://localhost:5000/teacher.html)

---

## 🧪 Automated Testing

Run the comprehensive unit test suite:
```bash
python -m unittest backend/tests/test_flashnova.py
```
This tests all 40 requirements:
- Student 10-digit enrollment validation & duplicates rejection
- Teacher account authentication & subject verification code validation
- Dynamic 10s QR rotation, expiry rejection & auto-enrollment
- Question creation, student answering & duplicate attempt prevention
- Privacy filter verification (verifying zero name leakage in teacher endpoints, CSV & PDF)
- Voluntary doubt consent workflow & teacher reply
- Real-time confusion tally aggregation
- File upload & download permissions

---

## 🌐 Deployment Instructions

### 1. Backend Hosting (Render)
1. Push the repository to GitHub: `https://github.com/anirudhatripathi24808-ux/Flash-Thinkers.git`.
2. In [Render Dashboard](https://dashboard.render.com/), select **New > Web Service**.
3. Connect your `Flash-Thinkers` repository.
4. Render will auto-detect `render.yaml` or you can configure manually:
   - **Environment:** `Python`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `gunicorn --worker-class simple_websocket.SimpleWebSocketServer -w 1 run:app`
5. Add Environment Variables:
   - `SECRET_KEY`: `<your-random-secret>`
   - `FLASK_ENV`: `production`
   - `CORS_ORIGINS`: `*`
6. Once deployed, note your service URL (e.g. `https://flashnova-backend.onrender.com`).

### 2. Frontend Hosting (GitHub Pages)
1. In your GitHub repository: `https://github.com/anirudhatripathi24808-ux/Flash-Thinkers/settings/pages`.
2. Under **Build and deployment**:
   - **Source:** `Deploy from a branch`
   - **Branch:** `main`
   - **Folder:** `/ (root)`
3. Save. GitHub Pages will build and deploy the site at:  
   `https://anirudhatripathi24808-ux.github.io/Flash-Thinkers/`
4. On the live frontend, click the **API Settings** button (top right) and set your deployed Render backend URL.

---

## 🔒 Security & Privacy Notice
- Never commit secret `.env` keys to GitHub.
- Full enrollment numbers are accessible only by the student in their private profile.
- Voluntary doubt identity disclosure occurs exclusively after explicit student consent.
- All backend endpoints validate roles using secure session tokens.

---
**FLASHNOVA** &copy; 2026. Hackathon Edition.
