import os
from supabase import Client, create_client
from datetime import datetime
from dotenv import load_dotenv
from .databaseCommands import db_select, db_insert, db_delete

defrost_default = 60

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


def del_cont(contID):
    history_cleared = clear_history(contID)
    relationsCount = db_delete("relation", "following_cont_id", contID)
    configCount = db_delete("config", "container_id", contID)
    return [relationsCount, configCount, history_cleared]


# Limpia el historial de un contenedor. Usar en caso de error o cambios, porque el historial se va a purgar regularmente.
# Mucho cuidado con usar este comando, ya que no reversible
def clear_history(contID):
    data, count = db_select("config", "signal_id", "container_id", contID)
    signal = data[0]["signal_id"]
    count = db_delete("signals", "idvigia", signal)
    return count


# Vincula un contenedor a un cliente. Ambos deben existir.
def link_cont_to_client(contID, clientID):
    client = return_client(clientID)
    if client == -1:
        return -1
    followedID = client["id"]
    data, count = db_select("config", "*", "container_id", contID)
    if count == 0:
        return -2
    # Ver si un contenedor ya está vinculado a un cliente
    followingID = data[1][0]["id"]
    data, count = db_insert("relation",{
        "following_cont_id": followingID,
        "followed_user_id": followedID,
    })
    return data


# Ingresa un contenedor al sistema, creando todas las relaciones necesarias. Es necesario asignar un cliente como minimo
# TODO: TESTEAR
def new_cont(clientID, contID, name):
    # Primero nos fijamos si el contenedor ya existe
    data, count = db_select("config", "*", "container_id", contID)
    if count > 0:
        return -1
    # Verificamos que el cliente existe, si no no vamos a poder asignar el contenedor
    client = return_client(clientID)
    if client == -1:
        return -2
    data, count = db_insert("config", {
        "container_id": contID,
        "display_name": name if name else "Sin nombre",
        "signal_id": contID  # Ver si cambiar esto
    })
    link_cont_to_client(contID, clientID)
    return data


# Vincula a un cliente con un contenedor.
# TODO: Testear
def assign_cont(clientID, contID, name):
    result = new_cont(clientID, contID, name)
    if result == -1:
        result = link_cont_to_client(contID, clientID)
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


# Comprueba si el defrost o el compresor está en un estado normal. De no ser así, se activa una alarma
# Se manda el campo a checkear en field, y la condición normal en checkIfTrue, ya que son opuestas
def check_hour_status(containerID, field, checkIfTrue):
    data, count = db_select("signals", "*", "idvigia", containerID, setOrder="date", setLimit=20)
    timeNow = datetime.now()
    # TODO: Ver si esto funciona correctamente
    for row in data:
        if row[field] == checkIfTrue:
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
def cont_status(containerID):
    data, count = db_select("signals", "*", "idvigia", containerID, setLimit=1)
    if count == 0:
        return -1
    else:
        status = data[0]
        alarma = defrost = False
        if controller_status(status["date"]):
            alarma = True
        if not status["defrost"]:
            defrost_status = check_hour_status(containerID, "defrost", False)
            if defrost_status:
                alarma = True
            else:
                defrost = True
        if not status["arranque_comp"]:
            compresor_status = check_hour_status(containerID, "arranque_comp", True)
            if compresor_status:
                alarma = True
        if status["bateria"]:
            alarma = True
        status["alarma"] = alarma
        status["defrost_status"] = defrost
        data, count = db_select("config", "*", "container_id", containerID)
        status["name"] = data[0]["display_name"]
        status["id"] = containerID
        return status


# Se fija que clientes están asignado a un contenedor en particular
def cont_assigned(contID):
    clients, count = db_select("config", "relation(*)", "container_id", contID)
    clientList = []
    for client in clients:
        data, count = db_select("relation", "client(*)", "followed_user_id", client['followed_user_id'])
        clientList.append(data)
    return clientList


# Devuelve el estados de todos los contenedores asignados a una cuenta
# TODO: Programar errores, que pasa si no existe el cliente o si no tiene contenedores asignados
def status_cont_client(clientID):
    relation, count = db_select("client", "relation(*)", "user_id", clientID)
    if count == 0:
        return -1
    all_cont_status = []
    for row in relation:
        data, count = db_select("config", "*", "id", row["following_cont_id"])
        status = cont_status(data[0]['signal_id'])
        all_cont_status.append(status)
    return all_cont_status


# Devuelve los datos de un cliente a traves de su ID
# TODO: Ver de eliminar esta función si no es muy necesaria
def return_client(clientID):
    data, count = db_select("client", "*", "user_id", clientID)
    if count == 0:
        return -1
    else:
        return data[0]


# Crea un cliente. Revisar luego de ver los permisos y el auth
def create_new_client(name, clientID):
    db = connect()
    data, count = db.table("client").insert({"title": name, "user_id": clientID}).execute()  # ver como asignar las id
    return data
