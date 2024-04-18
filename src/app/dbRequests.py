import os
from supabase import Client, create_client
from datetime import datetime
from dotenv import load_dotenv

defrost_default = 60

load_dotenv()
# Cargo las credenciales a través de un archivo
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')


# Código para conectarme a la DB
def connect():
    supabase: Client = create_client(url, key)

    return supabase


""" Esto se puede hacer directo en supabase. Averiguar
# Limpia las señales antiguas. El valor por defecto es 20
def delete_last_signals(cont_id):
    db = connect()
    data, count = (db.table("signals").
                   select("*", count='exact').
                   order("id", desc=True). #Ver si poner la fecha en vez de las id.
                   eq("idvigia", cont_id).
                   limit(1).execute())
"""


def test():
    return {"url":url,"key":key}


def del_cont(contID):
    db = connect()
    data, count = db.table("container").delete(count='exact').eq("following_cont_id", contID).execute()
    history_cleared = clear_history(contID)
    return [count[1], history_cleared]


# Limpia el historial de un contenedor. Usar en caso de error o cambios, porque el historial se va a purgar regularmente.
# Mucho cuidado con usar este comando, ya que no reversible
def clear_history(contID):
    db = connect()
    data, count = db.table("config").select("signal_id", count='exact').eq("container_id", contID).execute()
    signal = data[1][0]["signal_id"]
    data, count = db.table("signals").delete(count='exact').eq("idvigia", signal).execute()
    return count[1]


def link_cont_to_client(contID, clientID):
    db = connect()
    client = return_client(clientID)
    followedID = client["id"]
    data, count = (db.table("config").
                   select("*", count='exact').
                   eq("container_id", contID).
                   execute())
    followingID = data[1][0]["id"]
    data, count = db.table("relation").insert({
        "following_cont_id": followingID,
        "followed_user_id": followedID,
    }).execute()
    return data


# Ingresa un contenedor al sistema, creando todas las relaciones necesarias. Es necesario asignar un cliente como minimo
# TODO: TESTEAR
def new_cont(clientID, contID, name):
    db = connect()
    # Primero nos fijamos si el contenedor ya existe
    data, count = db.table("config").select("*", count='exact').eq("container_id", contID).execute()
    if count[1] > 0:
        return -1
    # Verificamos que el cliente existe, sino no vamos a poder asignar el contenedor
    client = return_client(clientID)
    if client == -1:
        return -2
    data, count = db.table("config").insert({
        "container_id": contID,
        "display_name": name if name else "Sin nombre",
        "signal_id": contID  # Ver si cambiar esto
    }).execute()
    link_cont_to_client(contID, clientID)
    return data


# Vincula a un cliente con un contenedor.
# TODO: Testear
def assign_cont(clientID, contID, name):
    result = new_cont(clientID, contID, name)
    if result == -1:
        result = link_cont_to_client(contID,clientID)
    return result


# Cambia el nombre de un contenedor
# TODO: Testear
def name_cont(contID, name):
    db = connect()
    data, count = (db.table("config").
                   update({"display_name": name}, count='exact').
                   eq("container_id", contID).
                   execute())
    if count[1] == 0:
        return 0
    elif count[1] == 1:
        return data
    else:
        return -1


# Comprueba si el defrost está en un estado normal. De no ser así, se activa una alarma
def check_defrost_status(cont_id, db):
    data, count = (db.table("signals").
                   select("*", count='exact').
                   order("date", desc=True).  # TODO: Ver si acomoda los datos de forma apropiada
                   eq("idvigia", cont_id).
                   limit(20).execute())
    timeNow = datetime.now()
    # TODO: Ver si esto funciona correctamente
    for row in data[1]:
        if not row["defrost"]:
            return False
        registeredDate = convert_date(row["date"])
        timeDelta = timeNow - registeredDate
        if timeDelta.total_seconds() / 60 > 60:
            return True


def convert_date(dateStr):
    strippedDate = dateStr[:-6]
    return datetime.strptime(strippedDate, "%Y-%m-%dT%H:%M:%S.%f")


# Verifica que el controlador este mandando señales. Si no mandó una por 35m devuelve un error
def controller_status(lastSignal):
    timeNow = datetime.now()
    lastSignalDT = convert_date(lastSignal)
    timeDelta = timeNow - lastSignalDT
    if timeDelta.total_seconds() / 60 > 35:
        return True
    else:
        return False


# Devuelve el estado de un contenedor en particular
def cont_status(containerID, connectionEstablished=False):
    if connectionEstablished:
        db = connectionEstablished
    else:
        db = connect()
    data, count = (db.table("signals").
                   select("*", count='exact').
                   order("id", desc=True).
                   eq("idvigia", containerID).
                   limit(1).execute())
    if count[1] == 0:
        return -1
    else:
        status = data[1][0]
        alarma = defrost = False
        if controller_status(status["date"]):
            alarma = True
        if not status["defrost"]:
            defrost_status = check_defrost_status(containerID, db)
            if defrost_status:
                alarma = True
            else:
                defrost = True
        if status["bateria"] or not status["compresor"] or not status["evaporacion"]:
            alarma = True
        status["alarma"] = alarma
        status["defrost_status"] = defrost
        data, count = (db.table("config").
                       select("*", count='exact').
                       eq("container_id", containerID).
                       execute())
        status["name"] = data[1][0]["display_name"]
        status["id"] = containerID
        return status


# Se fija que clientes están asignado a un contenedor en particular
def cont_assigned(contID):
    db = connect()
    data, count = (db.table("config").
                   select("relation(*)", count='exact').
                   eq("container_id", contID).
                   execute())
    clientList = []
    for client in data[1][0]['relation']:
        data, count = (db.table("relation").
                       select("client(*)", count='exact').
                       eq("followed_user_id", client['followed_user_id']).
                       execute())
        clientList.append(data[1][0]['client'])
    return clientList


# Devuelve el estados de todos los contenedores asignados a una cuenta
# TODO: Programar errores, que pasa si no existe el cliente o si no tiene contenedores asignados
def status_cont_client(clientID):
    db = connect()
    data, count = (db.table("client").
                   select("relation(*)", count='exact').
                   eq("user_id", clientID).
                   execute())
    all_cont_status = []
    for row in data[1][0]['relation']:
        data, count = (db.table("config").
                       select("*", count='exact').
                       eq("id", row["following_cont_id"]).
                       execute())
        status = cont_status(data[1][0]['signal_id'])
        all_cont_status.append(status)
    return all_cont_status


# Devuelve los datos de un cliente a traves de su ID
def return_client(clientID):
    db = connect()
    data, count = (db.table("client").
                   select("*", count='exact').
                   eq("user_id", clientID).
                   execute())
    if count[1] == 0:
        return -1
    else:
        return data[1][0]


# Crea un cliente. Revisar luego de ver los permisos y el auth
def create_new_client(name, clientID):
    db = connect()
    data, count = db.table("client").insert({"title": name, "user_id": clientID}).execute()  # ver como asignar las id
    return data
