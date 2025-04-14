import sqlite3
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import xml.etree.ElementTree as ET

app = FastAPI()
templates = Jinja2Templates(directory="templates")


def init_db():
    conn = sqlite3.connect("autosalon.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT NOT NULL,
        model TEXT NOT NULL,
        price REAL NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        phone TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        car_id INTEGER NOT NULL,
        client_id INTEGER NOT NULL,
        sale_date TEXT NOT NULL,
        FOREIGN KEY(car_id) REFERENCES cars(id),
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM cars")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO cars (brand, model, price) VALUES (?, ?, ?)", ("Toyota", "Camry", 25000))
        cursor.execute("INSERT INTO cars (brand, model, price) VALUES (?, ?, ?)", ("BMW", "X5", 50000))

    cursor.execute("SELECT COUNT(*) FROM clients")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO clients (full_name, phone) VALUES (?, ?)", ("Иван Иванов", "+79001112233"))
        cursor.execute("INSERT INTO clients (full_name, phone) VALUES (?, ?)", ("Анна Смирнова", "+79004445566"))

    conn.commit()
    conn.close()


init_db()

# GET endpoints
@app.get("/cars")
def get_cars():
    conn = sqlite3.connect("autosalon.db")
    conn.row_factory = sqlite3.Row
    cars = conn.cursor().execute("SELECT * FROM cars").fetchall()
    conn.close()
    return [dict(row) for row in cars]


@app.get("/clients")
def get_clients():
    conn = sqlite3.connect("autosalon.db")
    conn.row_factory = sqlite3.Row
    clients = conn.cursor().execute("SELECT * FROM clients").fetchall()
    conn.close()
    return [dict(row) for row in clients]


@app.get("/sales")
def get_sales():
    conn = sqlite3.connect("autosalon.db")
    conn.row_factory = sqlite3.Row
    sales = conn.cursor().execute("""
        SELECT sales.id, cars.brand || ' ' || cars.model AS car, clients.full_name AS client, sales.sale_date 
        FROM sales
        JOIN cars ON sales.car_id = cars.id
        JOIN clients ON sales.client_id = clients.id
    """).fetchall()
    conn.close()
    return [dict(row) for row in sales]

# POST endpoints
@app.post("/cars")
def add_car(brand: str, model: str, price: float):
    conn = sqlite3.connect("autosalon.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO cars (brand, model, price) VALUES (?, ?, ?)", (brand, model, price))
    conn.commit()
    conn.close()
    return {"message": "Car added successfully"}

@app.post("/clients")
def add_client(full_name: str, phone: str):
    conn = sqlite3.connect("autosalon.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO clients (full_name, phone) VALUES (?, ?)", (full_name, phone))
    conn.commit()
    conn.close()
    return {"message": "Client added successfully"}

@app.post("/sales")
def add_sale(car_id: int, client_id: int, sale_date: str):
    conn = sqlite3.connect("autosalon.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sales (car_id, client_id, sale_date) VALUES (?, ?, ?)", (car_id, client_id, sale_date))
    conn.commit()
    conn.close()
    return {"message": "Sale recorded successfully"}

# HTML form
@app.get("/create-sale", response_class=HTMLResponse)
def create_sale_form(request: Request):
    conn = sqlite3.connect("autosalon.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cars = cursor.execute("SELECT * FROM cars").fetchall()
    clients = cursor.execute("SELECT * FROM clients").fetchall()
    conn.close()
    return templates.TemplateResponse("create_sale.html", {"request": request, "cars": cars, "clients": clients})

@app.post("/create-sale", response_class=HTMLResponse)
def submit_sale_form(request: Request,
                     car_id: int = Form(...),
                     client_id: int = Form(...),
                     sale_date: str = Form(...)):
    conn = sqlite3.connect("autosalon.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sales (car_id, client_id, sale_date) VALUES (?, ?, ?)", (car_id, client_id, sale_date))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/sales", status_code=302)

# XML экспорт
@app.get("/export/clients")
def export_clients():
    conn = sqlite3.connect("autosalon.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients")
    clients = cursor.fetchall()
    conn.close()

    root = ET.Element("clients")
    for client in clients:
        el = ET.SubElement(root, "client")
        for key in client.keys():
            ET.SubElement(el, key).text = str(client[key])
    ET.ElementTree(root).write("clients.xml", encoding="utf-8", xml_declaration=True)
    return {"message": "Export complete", "file": "clients.xml"}

# XML импорт
@app.post("/import/clients")
def import_clients():
    tree = ET.parse("clients.xml")
    root = tree.getroot()

    conn = sqlite3.connect("autosalon.db")
    cursor = conn.cursor()

    for client in root.findall("client"):
        full_name = client.find("full_name").text
        phone = client.find("phone").text
        try:
            cursor.execute("INSERT INTO clients (full_name, phone) VALUES (?, ?)", (full_name, phone))
        except sqlite3.IntegrityError:
            continue
    conn.commit()
    conn.close()
    return {"message": "Import complete"}
