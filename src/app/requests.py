from .databaseCommands import *
from .logic import controller_status, check_hour_status


# Desvincula un contenedor, eliminando las relaciones de un usuario a él. Si era el único usuario, también elimina
# sus señales. TODO: Testear más a fondo
def unlink_cont(userID, contID, delCont=False):
    userTableID, count = db_select("client", "*", "user_id", userID)
    unlinkCount = db_delete("vigia_client", ["following_cont_id", "followed_user_id"], [contID, userTableID[0]["id"]])
    data, remainingRelations = db_select("vigia_client", "*", "following_cont_id", contID)
    if remainingRelations == 0:
        history_cleared = clear_history(contID)
    else:
        history_cleared = False
    return [True if unlinkCount > 0 else False, history_cleared]


# Limpia el historial de un contenedor. Usar en caso de error o cambios, porque el historial se va a purgar regularmente
# Mucho cuidado con usar este comando, ya que no reversible. Probablemente quede como comando administrativo.
def clear_history(contID):
    count = db_delete("signals", "idvigia", contID)
    return count


# Vincula un contenedor a un cliente. Ambos deben existir.
def link_cont_to_client(contID, userID, owner=True):
    data, count = db_select("client", "id", "user_id", userID)
    if count == 0:
        return -1
    followedUserID = data[0]["id"]
    data, count = db_select("vigia", "id", "id", contID)
    if count == 0:
        return -2
    followingContID = data[0]["id"]
    # Verificamos que ese contenedor no este asignado a esa cuenta antes de seguir
    data, count = db_select("vigia_client", "*",
                            match={"following_cont_id": followingContID, "followed_user_id": followedUserID})
    if count > 0:
        return -3
    data, count = db_insert("vigia_client", {
        "following_cont_id": followingContID,
        "followed_user_id": followedUserID,
    })
    return data


# Ingresa un contenedor al sistema, creando todas las relaciones necesarias.
# TODO: TESTEAR
def new_cont(name, password, config):
    data, count = db_select("config", "id", "config_name", config)
    if count == 1:
        configID = data[0]["id"]
    else:
        return {"error": "No existe la configuración ingresada."}
    data, count = db_insert("vigia", {
        "display_name": name if name else "Sin nombre",
        "password": password,
        "config_id": configID
    })
    return data


# Cambia el nombre de un contenedor
# TODO: Testear
def name_cont(contID, name):
    count = db_update("vigia", {"display_name": name}, "id", contID)
    if count == 0:
        return 0
    elif count == 1:
        return count
    else:
        return -1


# Devuelve el estado de un contenedor en particular
def cont_status(containerID, detail=False):
    # TODO: Ver si el limite = 20 es adecuado, podría ser menos
    data, count = db_fetch_signals(containerID)
    if count == 0:
        return {"error": "No se encontró el contenedor."}
    if len(data['signals']) == 0:
        if detail:
            return {
                "id": containerID,
                "name": data["display_name"],
                "temp": 999,
                "bateria": None,
                "defrost": None,
                "compresor": None,
                "evaporacion": None,
                "arranque_comp": None,
                "alarm_list": ["No hay señales"],
                "defrost_status": False,
            }
        else:
            return {
                "name": data["display_name"],
                "id": containerID,
                "alarm_list": ["No hay señales"],
                "defrost_status": False,
            }
    else:
        signals = data["signals"]
        config = data["config"]
        alarma = []
        defrost = False
        if controller_status(signals[0]["date"], config["inactivity_time"]):
            alarma.append(f"Más de {config["inactivity_time"]} minutos de inactividad.")
        if signals[0]["defrost"] and config["check_defrost"]:
            defrost_status = check_hour_status(signals, "defrost", True, config["defrost_timer"])
            if defrost_status:
                alarma.append(f"El defrost está activado hace más de {config["defrost_timer"]} minutos.")
            else:
                defrost = True
        if not signals[0]["arranque_comp"] and config["check_compresor"]:
            compresor_status = check_hour_status(signals, "arranque_comp", True, config["compresor_timer"])
            if compresor_status:
                alarma.append(f"El compresor está desactivado hace más de {config["compresor_timer"]} minutos.")
        if signals[0]["bateria"] and config["check_power"]:
            alarma.append("La batería está activada, problemas de alimentación.")
        if detail:
            lastSignal = signals[0]
            lastSignal["defrost_status"] = defrost
            lastSignal["name"] = data["display_name"]
            lastSignal["id"] = containerID
            lastSignal["alarm_list"] = alarma
            return lastSignal
        else:
            return {
                "name": data["display_name"],
                "id": containerID,
                "alarm_list": alarma,
                "defrost_status": defrost,
            }


# Se fija que clientes están asignados a un contenedor en particular
def cont_assigned(contID):
    clients, count = db_select("vigia", "vigia_client(*)", "id", contID)
    clientList = []
    for client in clients:
        data, count = db_select("vigia_client", "client(*)", "followed_user_id", client['followed_user_id'])
        clientList.append(data)
    return clientList


# Devuelve el estado de todos los contenedores asignados a una cuenta
def status_cont_client(clientID):
    contIDList, count = db_select("client", "vigia(id)", "user_id", clientID)
    if count == 0:
        # TODO: Testear esto
        return False
    all_cont_status = []
    for contID in contIDList[0]['vigia']:
        status = cont_status(contID['id'])
        all_cont_status.append(status)
    return all_cont_status


# Verifica si el contenedor pertenece al usuario
def check_ownership(clientID, contID):
    count = db_check_relation(clientID, contID)
    if count > 0:
        return True
    else:
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
    data, count = db_select("vigia", "password", "id", contID)
    if count == 1:
        if data[0]['password'] == password:
            return True
        else:
            return -1
    return 0
