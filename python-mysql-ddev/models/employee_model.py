#from config import get_db_connection
#from models.db import get_connection
from db import get_db_connection

def get_employees(search, limit, offset):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"

    cur.execute("""
        SELECT * FROM employees
        WHERE name LIKE %s OR email LIKE %s
        ORDER BY id DESC
        LIMIT %s OFFSET %s
    """, (like, like, limit, offset))

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data


def get_employee_count(search):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM employees
        WHERE name LIKE %s OR email LIKE %s
    """, (like, like))

    total = cur.fetchone()["total"]
    cur.close()
    conn.close()
    return total


def get_employee_by_id(emp_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees WHERE id=%s", (emp_id,))
    data = cur.fetchone()
    cur.close()
    conn.close()
    return data


def insert(name, email):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO employees (name,email) VALUES (%s,%s)",
        (name, email)
    )
    conn.commit()
    cur.close()
    conn.close()


def update(emp_id, name, email):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE employees SET name=%s, email=%s WHERE id=%s",
        (name, email, emp_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def delete(emp_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM employees WHERE id=%s", (emp_id,))
    conn.commit()
    cur.close()
    conn.close()

def search_employees(q):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM employees WHERE name LIKE %s OR email LIKE %s",
        (f"%{q}%", f"%{q}%")
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def create_employee(name, email):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO employees (name, email) VALUES (%s, %s)",
        (name, email)
    )
    conn.commit()
    cur.close()
    conn.close()
