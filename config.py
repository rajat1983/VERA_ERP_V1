# DB_CONFIG = {
#     "host": "db",
#     "user": "root",
#     "password": "root",
#     "database": "flask_app",
#     "port": 3306
# }
import pymysql

def get_db_connection():
    return pymysql.connect(
        host="db",
        user="root",
        password="root",
        database="vera_erp",
        cursorclass=pymysql.cursors.DictCursor
    )
