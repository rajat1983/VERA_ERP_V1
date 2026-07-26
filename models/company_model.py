from db import get_db_connection


def get_company():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM company
        LIMIT 1
    """)

    company = cur.fetchone()

    cur.close()
    conn.close()

    return company