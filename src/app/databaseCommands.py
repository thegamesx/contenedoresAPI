from dotenv import load_dotenv
import os
from supabase import Client, create_client

load_dotenv()
# Cargo las credenciales a través de un archivo
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

API_email = os.getenv('API_EMAIL')
API_password = os.getenv('API_PASSWORD')


# Código para conectarme a la DB
def connect():
    supabase: Client = create_client(url, key)
    try:
        # Cambiar esto luego con el usuario y contraseña que corresponda
        data = supabase.auth.sign_in_with_password({"email": API_email, "password": API_password})
    except:
        return -1
    return supabase


def db_select(table, columns, equalColumn, equalValue, setOrder="id", setLimit=None):
    db = connect()
    data, count = (db.table(table).
                   select(columns, count='exact').
                   eq(equalColumn, equalValue).
                   order(setOrder, desc=True).
                   limit(setLimit).
                   execute())
    # Ver como está compuesta la data y devolverla lo más prolija posible
    try:
        return data[1][0][columns[:-3]], count[1]
    except:
        return data[1], count[1]


# TODO: Hacer esto
def db_update():
    pass

def db_delete(table, equalColumn, equalValue):
    db = connect()
    data, count = db.table(table).delete(count='exact').eq(equalColumn, equalValue).execute()
    return count[1]


def db_insert(table, dataDict):
    db = connect()
    data, count = db.table(table).insert(dataDict).execute()
    return data, count[1]
