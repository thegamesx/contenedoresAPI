from .databaseCommands import db_select, db_insert, db_delete, db_update
from .logic import controller_status, check_hour_status

defrost_default = 60


# Desvincula un contenedor, eliminando las relaciones de un usuario a él. Si era el único usuario, también elimina
# sus señales. TODO: Testear más a fondo
def unlink_cont(userID, contID, delCont=False):
    userTableID, count = db_select("client", "*", "user_id", userID)
    unlinkCount = db_delete("relation", ["following_cont_id", "followed_user_id"], [contID, userTableID[0]["id"]])
    data, remainingRelations = db_select("relation", "*", "following_cont_id", contID)
    if remainingRelations == 0:
        history_cleared = clear_history(contID)
    else:
        history_cleared = False
    return [True if unlinkCount > 0 else False, history_cleared]


# Limpia el historial de un contenedor. Usar en caso de error o cambios, porque el historial se va a purgar regularmente
# Mucho cuidado con usar este comando, ya que no reversible. Probablemente quede como comando administrativo.
def clear_history(contID):
    data, count = db_select("config", "signal_id", "container_id", contID)
    signal = data[0]["signal_id"]
    count = db_delete("signals", "idvigia", signal)
    return count


# Vincula un contenedor a un cliente. Ambos deben existir.
def link_cont_to_client(contID, userID, owner=True):
    data, count = db_select("client", "*", "user_id", userID)
    if count == 0:
        return -1
    followedUserID = data[0]["id"]
    data, count = db_select("config", "*", "container_id", contID)
    if count == 0:
        return -2
    followingContID = data[0]["id"]
    # Verificamos que ese contenedor no este asignado a esa cuenta antes de seguir
    data, count = db_select("relation", "*",
                            match={"following_cont_id": followingContID, "followed_user_id": followedUserID})
    if count > 0:
        return -3
    data, count = db_insert("relation", {
        "following_cont_id": followingContID,
        "followed_user_id": followedUserID,
        "ownership": owner
    })
    return data


# Ingresa un contenedor al sistema, creando todas las relaciones necesarias.
# TODO: TESTEAR
def new_cont(contID, name, password):
    # Primero nos fijamos si el contenedor ya existe
    data, count = db_select("config", "*", "container_id", contID)
    if count > 0:
        return -1
    data, count = db_insert("config", {
        "container_id": contID,
        "display_name": name if name else "Sin nombre",
        "signal_id": contID,  # Ver si cambiar esto
        "password": password
    })
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


# Devuelve el estado de un contenedor en particular
# TODO: Revisar y testear las señales
def cont_status(containerID):
    data, count = db_select("signals", "*", "idvigia", containerID, setLimit=20)
    if count == 0:
        return -1
    else:
        status = data[0]
        alarma = []
        defrost = False
        if controller_status(status["date"]):
            alarma.append("Más de una media hora sin actividad.")
        if status["defrost"]:
            defrost_status = check_hour_status(data, "defrost", True)
            if defrost_status:
                alarma.append("El defrost está activado hace más de una hora.")
            else:
                defrost = True
        if not status["arranque_comp"]:
            compresor_status = check_hour_status(data, "arranque_comp", True)
            if compresor_status:
                alarma.append("El compresor está desactivado hace más de una hora.")
        if status["bateria"]:
            alarma.append("La batería está activada, problemas de alimentación.")
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


# Devuelve el estado de todos los contenedores asignados a una cuenta
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
# TODO: Ver si es necesario mantener esto. Cambiaron las especificaciones.
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
    return data[0]


def check_client_exists(clientID=None, username=None):
    if (clientID and username) or (not clientID and not username):
        return -2
    data, count = db_select("client", "*", "user_id" if clientID else "name", clientID if clientID else username)
    if count == 0:
        return -1
    return data[0]


def check_cont_password(contID, password):
    data, count = db_select("config", "*", "container_id", contID)
    if count == 1:
        if data[0]['password'] == password:
            return True
        else:
            return -1
    return 0
