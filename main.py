from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import hashlib
import time
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3, hashlib
# --- VORISLIK VA POLIMORFIZM ---
class BazaAmali:
    def __init__(self, db_name="oshxona.db"):
        self.db_name = db_name
    def bajar(self):
        pass

class MahsulotBoshqaruv(BazaAmali): # Vorislik
    def bajar(self, amal_nomi): # Polimorfizm
        return f"Hozirgi bajarilayotgan amal: {amal_nomi}"

# Klasdan obyekt olamiz
oop_helper = MahsulotBoshqaruv()
# ------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect("menu.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        );
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            emoji TEXT,
            name TEXT NOT NULL,
            desc TEXT,
            price INTEGER NOT NULL,
            category TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_login TEXT,
            time TEXT,
            status TEXT DEFAULT 'yangi',
            items TEXT,
            total INTEGER,
            address TEXT,
            lat REAL,
            lng REAL
        );
        CREATE TABLE IF NOT EXISTS ratings (
            product_id TEXT,
            user_login TEXT,
            score INTEGER,
            PRIMARY KEY (product_id, user_login)
        );
    """)
    # Default admin va kuryer
    try:
        c.execute("INSERT INTO users (login, name, password, role) VALUES (?, ?, ?, ?)",
                  ('admin', 'Admin', '1234', 'admin'))
        c.execute("INSERT INTO users (login, name, password, role) VALUES (?, ?, ?, ?)",
                  ('kuryer1', 'Ali Kuryer', '1234', 'courier'))
    except: pass
    conn.commit()
    conn.close()

init_db()

# AUTH
@app.post("/api/register")
def register(data: dict):
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (login, name, password, role) VALUES (?, ?, ?, ?)",
                     (data['login'], data['name'], data['password'], data.get('role', 'user')))
        conn.commit()
        return {"ok": True}
    except:
        raise HTTPException(400, "Bu login band!")
    finally:
        conn.close()

@app.post("/api/login")
def login(data: dict):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE login=? AND password=?",
                        (data['login'], data['password'])).fetchone()
    conn.close()
    if not user:
        raise HTTPException(401, "Login yoki parol noto'g'ri!")
    return {"login": user['login'], "name": user['name'], "role": user['role']}

@app.get("/api/users")
def get_users():
    conn = get_db()
    users = conn.execute("SELECT login, name, role FROM users").fetchall()
    conn.close()
    return [dict(u) for u in users]

@app.put("/api/users/{login}/name")
def update_name(login: str, data: dict):
    conn = get_db()
    conn.execute("UPDATE users SET name=? WHERE login=?", (data['name'], login))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.put("/api/users/{login}/password")
def update_password(login: str, data: dict):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE login=? AND password=?",
                        (login, data['old'])).fetchone()
    if not user:
        raise HTTPException(400, "Joriy parol noto'g'ri!")
    conn.execute("UPDATE users SET password=? WHERE login=?", (data['new'], login))
    conn.commit()
    conn.close()
    return {"ok": True}

# PRODUCTS
@app.get("/api/products")
def get_products():
    conn = get_db()
    rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    result = {"milliy": [], "fastfood": [], "ichimlik": []}
    for r in rows:
        d = dict(r)
        if d['category'] in result:
            result[d['category']].append(d)
    return result

@app.post("/api/products")
def add_product(data: dict):
    conn = get_db()
    pid = data.get('category', 'x')[0] + str(int(__import__('time').time()*1000))
    conn.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?)",
                 (pid, data.get('emoji','🍽️'), data['name'], data.get('desc',''), data['price'], data['category']))
    conn.commit()
    conn.close()
    return {"ok": True, "id": pid}

@app.delete("/api/products/{pid}")
def delete_product(pid: str):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.put("/api/products/{pid}")
def update_product(pid: str, data: dict):
    conn = get_db()
    conn.execute("UPDATE products SET name=?, price=? WHERE id=?",
                 (data['name'], data['price'], pid))
    conn.commit()
    conn.close()
    return {"ok": True}

# ORDERS
@app.get("/api/orders")
def get_orders():
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY time DESC").fetchall()
    conn.close()
    import json
    result = []
    for r in rows:
        d = dict(r)
        d['items'] = json.loads(d['items'])
        d['delivery'] = {'lat': d.pop('lat'), 'lng': d.pop('lng'), 'address': d.pop('address')}
        result.append(d)
    return result

@app.post("/api/orders")
def create_order(data: dict):
    import json, time
    conn = get_db()
    oid = 'ORD' + str(int(time.time()*1000))
    conn.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (oid, data['user'], data['time'], 'yangi',
                  json.dumps(data['items']), data['total'],
                  data['delivery']['address'], data['delivery']['lat'], data['delivery']['lng']))
    conn.commit()
    conn.close()
    return {"ok": True, "id": oid}

@app.put("/api/orders/{oid}/status")
def update_order_status(oid: str, data: dict):
    conn = get_db()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (data['status'], oid))
    conn.commit()
    conn.close()
    return {"ok": True}

# RATINGS
@app.post("/api/ratings")
def rate(data: dict):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO ratings VALUES (?, ?, ?)",
                 (data['product_id'], data['user'], data['score']))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.get("/api/ratings")
def get_ratings():
    conn = get_db()
    rows = conn.execute("SELECT * FROM ratings").fetchall()
    conn.close()
    return [dict(r) for r in rows]