# TabStash 🗄️

> Close your tabs. Keep your focus. 

TabStash is a full-stack, decoupled web application designed to act as an encrypted intelligence vault for browser tabs. Paste a messy URL, and the Python backend instantly visits the site, scrapes the OpenGraph metadata, and securely stashes it in a relational database for later viewing.

## 🚀 Tech Stack

**Backend:** Python, FastAPI, SQLite, Passlib (Bcrypt), JWT Auth, BeautifulSoup4, httpx
**Frontend:** Vanilla JavaScript, HTML5, Tailwind CSS

## 🧠 Architectural Decisions

### Why Vanilla JS instead of React?
I deliberately chose a zero-dependency, Vanilla JavaScript frontend for this project. Rather than hiding behind a framework's abstraction layer, I wanted to demonstrate a fundamental mastery of:
* Direct DOM manipulation and state synchronization.
* Native browser APIs (managing secure JWT sessions via `localStorage`).
* Handling asynchronous `fetch` requests and CORS communication with an independent backend.
* Building a lightweight, blazing-fast client with zero compilation steps.

### AI-Assisted Design Workflow
The backend architecture, database schema, API routing, and security protocols were built and wired manually. For the frontend UI/UX, I leveraged AI to rapidly prototype the Tailwind CSS layouts and establish a premium design language. This reflects my approach to a modern developer workflow: focusing my engineering time on complex backend logic and data pipelines, while utilizing AI tools to accelerate front-end styling and component design.

## ✨ Core Features
* **Asynchronous Web Scraping:** Uses `httpx` and `BeautifulSoup4` to fetch and parse `<title>` and `og:image` tags in milliseconds.
* **Stateless Security:** Passwords are mathematically hashed via Bcrypt. Sessions are managed entirely through secure, expiring JSON Web Tokens (JWT).
* **Relational Database:** Built on a strictly typed SQLite database enforcing `PRAGMA foreign_keys = ON` for cascading deletes between User, Category, and Tab tables.
* **Custom UI Components:** Features promise-based custom modal dialogs and an Intersection Observer for smooth scroll-reveal animations.

## 🛠️ How to Run Locally

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/tabstash.git
cd tabstash
```

2. **Install Python dependencies**
```bash
pip install fastapi uvicorn httpx beautifulsoup4 pyjwt passlib[bcrypt]
```

3. **Start the FastAPI Server**
```bash
python -m uvicorn main:app --reload
```
*(Note: The `tabstash.db` file is in the .gitignore. Running the server for the first time will automatically initialize a fresh relational database).*

4. **Launch the Frontend**
Open `index.html` in any modern web browser. No Node.js or build steps required.