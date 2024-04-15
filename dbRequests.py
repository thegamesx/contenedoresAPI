import json
from supabase import Client, create_client
from datetime import datetime

defrost_default = 60  # Preguntar si está bien


# Código para conectarme a la DB
def connect():
    # Cargo las credenciales a través de un archivo
    with open('dbCredentials.json', 'r') as jsonFile:
        credentials = json.load(jsonFile)
    url = credentials['url']
    key = credentials['key']

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


def del_cont(contID):
    db = connect()
    data, count = db.table("container").delete(count='exact').eq("following_signal_id", contID).execute()
    history_cleared = clear_history(contID)
    return [count[1], history_cleared]


# Limpia el historial de un contenedor. Usar en caso de error o cambios, porque el historial se va a purgar regularmente.
# Mucho cuidado con usar este comando, ya que no reversible
def clear_history(contID):
    db = connect()
    data, count = db.table("signals").delete(count='exact').eq("idvigia", contID).execute()
    return count[1]


# Ingresa un contenedor al sistema, creando todas las relaciones necesarias. Es necesario asignar un cliente como minimo
# TODO: TESTEAR
def new_cont(clientID, contID, name):
    db = connect()
    # Primero nos fijamos si el contenedor ya existe
    data, count = db.table("config").select("*", count='exact').eq("container_id", contID).execute()
    if count > 0:
        return {"error": "El contenedor ingresado ya existe."}
    # Verificamos que el cliente existe, sino no vamos a poder asignar el contenedor
    data, count = db.table("client").select("*", count='exact').eq("user_id", clientID).execute()
    if count == 0:
        return {"error": "No existe el cliente. Ingrese un cliente válido."}
    data, count = db.table("config").insert({
        "container_id": contID,
        "display_name": name if name else "Sin nombre",
        "signal_id": contID  # Ver si cambiar esto
    }).execute()
    followingID = data["id"]
    data, count = db.table("client").select("id", count='exact').eq("user_id", clientID).execute()
    followedID = data["id"]
    data, count = db.table("relation").insert({
        "following_signal_id": followingID,
        "followed_user_id": followedID,
    }).execute()
    return data


# Vincula a un cliente con un contenedor.
# TODO: Testear
def assign_cont(clientID, contID, name):
    db = connect()
    exists = db.table("container").select("*", count='exact').eq("followed_user_id", clientID).eq("following_signal_id",
                                                                                                  contID).execute()
    if exists.count == 0:
        data, count = (db.table("container")
                       .insert({
            "followed_user_id": clientID,
            "following_signal_id": contID,
            "display_name": name if name else "Sin nombre",
            "defrost_timer": defrost_default})  # Ver aca
                       .execute())
    else:
        return -1
    return data


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
        data = data[1][0]
        alarma = defrost = False
        # TODO: Programar el warning
        if controller_status(data["date"]):
            alarma = True
        if not data["defrost"]:
            defrost_status = check_defrost_status(containerID, db)
            if defrost_status:
                alarma = True
        if data["bateria"] or not data["compresor"] or not data["evaporacion"]:
            alarma = True
        data["alarma"] = alarma
        data["defrost_status"] = defrost
        return data


# Devuelve el estados de todos los contenedores asignados a una cuenta
# TODO: Testear con multiples contenedores
def status_cont_client(clientID):
    db = connect()
    data, count = (db.table("client").
                   select("relation(*)", count='exact').
                   eq("user_id", clientID).
                   execute())
    all_cont_status = []
    for row in data[1]:
        data, count = (db.table("config").
                       select("*", count='exact').
                       eq("id", row['relation']["following_signal_id"]).
                       execute())
        status = cont_status(data[1][0]['signal_id'])
        status["name"] = data[1][0]["display_name"]
        status["id"] = data[1][0]["container_id"]
        all_cont_status.append(status)
    return all_cont_status


# Crea un cliente. Revisar luego de ver los permisos y el auth
def createClient(name, id):
    db = connect()
    data, count = db.table("client").insert({"title": name, "user_id": id}).execute()  # ver como asignar las id
    return data
