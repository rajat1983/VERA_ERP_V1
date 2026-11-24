import os

import pymysql

from utils.security import is_production


def get_db_connection():
    if is_production():
        host = os.environ["DB_HOST"]
        user = os.environ["DB_USER"]
        password = os.environ["DB_PASSWORD"]
        database = os.environ["DB_NAME"]
    else:
        host = os.environ.get("DB_HOST", "db")
        user = os.environ.get("DB_USER", "root")
        password = os.environ.get("DB_PASSWORD", "root")
        database = os.environ.get("DB_NAME", "vera_erp")
    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor,
    )
