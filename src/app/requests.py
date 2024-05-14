from datetime import datetime
from .databaseCommands import db_select, db_insert, db_delete, db_update

defrost_default = 60

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
# Mucho cuidado con usar este comando, ya que no reversible. Probablemente quede como comando administrativo.
def clear_history(contID):
    data, count = db_select("config", "signal_id", "container_id", contID)
    signal = data[0]["signal_id"]
    count = db_delete("signals", "idvigia", signal)
    return count


# Vincula un contenedor a un cliente. Ambos deben existir.
def link_cont_to_client(contID, clientID, owner=False):
    data, count = db_select("client", "*", "user_id", clientID)
    if count == 0:
        return -1
    followedID = data[0]["id"]
    data, count = db_select("config", "*", "container_id", contID)
    if count == 0:
        return -2
    followingID = data[0]["id"]
    # Verificamos que ese contenedor no este asignado a esa cuenta antes de seguir
    data, count = db_select("relation", "*", match={"following_cont_id": followingID, "followed_user_id": followedID})
    if count > 0:
        return -3
    data, count = db_insert("relation", {
        "following_cont_id": followingID,
        "followed_user_id": followedID,
        "ownership": owner
    })
    return data


# Ingresa un contenedor al sistema, creando todas las relaciones necesarias. Es necesario asignar un cliente como minimo
# TODO: TESTEAR
def new_cont(clientID, contID, name, owner=False, exist=True):
    # Primero nos fijamos si el contenedor ya existe
    data, count = db_select("config", "*", "container_id", contID)
    if count > 0:
        return -1
    # Verificamos que el cliente existe, si no no vamos a poder asignar el contenedor
    data, count = db_select("client", "*", "user_id", clientID)
    if count == 0:
        return -2
    # Por último, vemos si el contenedor tiene señales. Esta es una forma de autenticar el contendor y que no se
    # ingrese cualquier cosa.
    if exist:
        data, count = db_select("signals", "*", "idvigia", contID)
        if count == 0:
            return -3
    data, count = db_insert("config", {
        "container_id": contID,
        "display_name": name if name else "Sin nombre",
        "signal_id": contID  # Ver si cambiar esto
    })
    link_cont_to_client(contID, clientID, owner)
    return data


# Cambia el nombre de un contenedor
# TODO: Testear
def name_cont(contID, name):
    count = db_update("config", {"display_name": name}, "container_id", contID)
    if count == 0:
        return 0
    elif count == 1:
        return count
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


# Se fija que clientes están asignados a un contenedor en particular
def cont_assigned(contID):
    clients, count = db_select("config", "relation(*)", "container_id", contID)
    clientList = []
    for client in clients:
        data, count = db_select("relation", "client(*)", "followed_user_id", client['followed_user_id'])
        clientList.append(data)
    return clientList


# Devuelve el estados de todos los contenedores asignados a una cuenta
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


# Verifica si el contenedor pertenece al usuario
def check_ownership(clientID, contID):
    dataClient, count = db_select("client", "relation(*)", "user_id", clientID)
    for rowClient in dataClient:
        dataCont, count2 = db_select("config", "relation(*)", "container_id", contID)
        for rowCont in dataCont:
            if rowClient["following_cont_id"] == rowCont["following_cont_id"]:
                if rowClient["ownership"]:
                    return True
    return False


# Crea un cliente. Usa el ID del Auth0 como identificador.
def create_new_client(name, clientID):
    # Primero nos fijamos si existe
    data, count = db_select("client", "*", "user_id", clientID)
    if count > 0:
        return -1
    data, count = db_insert("client", {"name": name, "user_id": clientID})
    return data
