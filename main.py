import sqlite3
import re
import httpx 
from bs4 import BeautifulSoup 
from datetime import datetime, timedelta
import jwt
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials 
from fastapi.middleware.cors import CORSMiddleware 
from pydantic import BaseModel, field_validator
from passlib.context import CryptContext
from typing import Optional

app = FastAPI()
DB_FILE = "tabstash.db"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# SECURITY & JWT CONFIGURATION
# ==========================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "YOUR-OWN-SECRET-KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120 

security = HTTPBearer() 

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired! Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token!")

# ==========================================
# ADVANCED DATABASE SETUP (Relational)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON") 
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            hashed_password TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tabs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER, 
            url TEXT NOT NULL,
            title TEXT,
            image_url TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ==========================================
# WEB SCRAPER LOGIC
# ==========================================
async def fetch_link_data(url: str):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else "Unknown Title"
        
        image_url = None
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            image_url = og_image["content"]
            
        if not image_url:
            image_url = "https://images.unsplash.com/photo-1618401471353-b98afee0b2eb?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
            
        return {"title": title.strip(), "image_url": image_url}
        
    except Exception as e:
        return {"title": url, "image_url": "https://images.unsplash.com/photo-1618401471353-b98afee0b2eb?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"}

# ==========================================
# DATA BLUEPRINTS
# ==========================================
class UserCreate(BaseModel):
    username: str
    display_name: str
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, password: str):
        if len(password) < 8: raise ValueError("Password must be at least 8 characters.")
        if not re.search(r"\d", password): raise ValueError("Password must contain a number.")
        if not re.search(r"[A-Z]", password): raise ValueError("Password must contain an uppercase letter.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): raise ValueError("Password must contain a special character.")
        return password

class UserLogin(BaseModel):
    username: str
    password: str

class CategoryCreate(BaseModel):
    name: str

class TabCreate(BaseModel):
    url: str
    category_id: Optional[int] = None 

# ==========================================
# PUBLIC ROUTES
# ==========================================
@app.post("/register")
def register_user(user: UserCreate):
    # FIX: Truncate password to 72 bytes before hashing to prevent bcrypt crashes
    hashed_pw = get_password_hash(user.password[:72])
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, display_name, hashed_password) VALUES (?, ?, ?)",
            (user.username, user.display_name, hashed_pw))
        conn.commit()
        return {"message": "Account created successfully!"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username taken.")
    finally:
        conn.close()

@app.post("/login")
def login_user(credentials: UserLogin):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, display_name, hashed_password FROM users WHERE username = ?", (credentials.username,))
    user_record = cursor.fetchone()
    conn.close()

    # FIX: Truncate password to 72 bytes before verifying to prevent bcrypt crashes
    if not user_record or not verify_password(credentials.password[:72], user_record[2]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(data={"user_id": user_record[0], "display_name": user_record[1]})
    return {"access_token": token, "token_type": "bearer", "display_name": user_record[1]}

# ==========================================
# CATEGORY ROUTES
# ==========================================
@app.post("/categories")
def create_category(category: CategoryCreate, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)", (user_id, category.name))
    conn.commit()
    conn.close()
    return {"message": "Folder created!"}

@app.get("/categories")
def get_categories(user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM categories WHERE user_id = ? ORDER BY id ASC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    categories = [{"id": row[0], "name": row[1]} for row in rows]
    return {"categories": categories}

@app.delete("/categories/{cat_id}")
def delete_category(cat_id: int, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON") 
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id))
    conn.commit()
    conn.close()
    return {"message": "Folder and all its tabs deleted"}

# ==========================================
# TAB ROUTES
# ==========================================
@app.post("/tabs")
async def create_tab(tab: TabCreate, user_id: int = Depends(get_current_user)):
    scraped_data = await fetch_link_data(tab.url)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tabs (user_id, category_id, url, title, image_url) VALUES (?, ?, ?, ?, ?)",
        (user_id, tab.category_id, tab.url, scraped_data["title"], scraped_data["image_url"])
    )
    conn.commit()
    conn.close()
    return {"message": "Tab stashed!"}

@app.get("/tabs")
def get_tabs(category_id: Optional[int] = None, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if category_id:
        cursor.execute("SELECT id, url, title, image_url FROM tabs WHERE user_id = ? AND category_id = ? ORDER BY id DESC", (user_id, category_id))
    else:
        cursor.execute("SELECT id, url, title, image_url FROM tabs WHERE user_id = ? ORDER BY id DESC", (user_id,))
        
    rows = cursor.fetchall()
    conn.close()
    
    tabs = [{"id": row[0], "url": row[1], "title": row[2], "image_url": row[3]} for row in rows]
    return {"tabs": tabs}

@app.delete("/tabs/{tab_id}")
def delete_tab(tab_id: int, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tabs WHERE id = ? AND user_id = ?", (tab_id, user_id))
    conn.commit()
    conn.close()
    return {"message": "Tab deleted"}

@app.delete("/tabs")
def clear_stash(category_id: Optional[int] = None, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if category_id:
        cursor.execute("DELETE FROM tabs WHERE user_id = ? AND category_id = ?", (user_id, category_id))
    else:
        cursor.execute("DELETE FROM tabs WHERE user_id = ?", (user_id,))
        
    conn.commit()
    conn.close()
    return {"message": "Stash cleared"}
