import json
from supabase import Client, create_client

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


# Vincula a un cliente con un contenedor.
def assign_cont(clientID, contID, name, defrost):
    db = connect()
    exists = db.table("container").select("*", count='exact').eq("followed_user_id", clientID).eq("following_signal_id",
                                                                                                  contID).execute()
    if exists.count == 0:
        data, count = (db.table("container")
                       .insert({
            "followed_user_id": clientID,
            "following_signal_id": contID,
            "display_name": name if name else "Sin nombre",
            "defrost_timer": defrost if defrost else defrost_default})
                       .execute())
    else:
        return -1
    return data


# Cambia el nombre de un contenedor y/o actualiza el parámetro de defrost.
# Ver si es necesario establecer minimos y maximos por seguridad
def name_cont(contID, name, defrost):
    db = connect()
    if name and defrost:
        updateQuery = {"display_name": name, "defrost_timer": defrost}
    elif name:
        updateQuery = {"display_name": name}
    else:
        updateQuery = {"defrost_timer": defrost}
    data, count = (db.table("container").
                   update(updateQuery, count='exact').
                   eq("following_signal_id", contID).
                   execute())
    if count[1] == 0:
        return 0
    elif count[1] == 1:
        return data
    else:
        return -1


# Comprueba si el defrost está en un estado normal. De no ser así, se activa una alarma
def check_defrost_status(cont_id, db):
    data, count = (db.table("container").
                   select("*", count='exact').
                   eq("following_signal_id", cont_id).
                   execute())
    # Ver como hacer si encuentra más de una conf de container (arreglar la db)
    if count[1]==1:
        timer = data[1][0]["defrost_timer"]
        data, count = (db.table("signals").
                       select("*", count='exact').
                       order("id", desc=True).
                       eq("idvigia", cont_id).
                       limit(20).execute())
        inactive_time=0
        # Ver como calcular el tiempo entre entradas en la db


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
        alarma, warning = False
        # Programar el warning
        if not data["defrost"]:
            defrost_status = check_defrost_status(containerID, db)
            if defrost_status:
                alarma = True
        if data["bateria"] or not data["compresor"] or not data["evaporacion"]:
            alarma = True
        data["alarma"] = alarma
        return data


#Devuelve el estados de todos los contenedores asignados a una cuenta
def status_cont_client(clientID):
    db = connect()
    data, count = (db.table("container").
                   select("*", count='exact').
                   eq("followed_user_id", clientID).
                   execute())
    all_cont_status = []
    for row in data[1]:
        all_cont_status.append(cont_status(row["following_signal_id"],db))


# Crea un cliente. Revisar luego de ver los permisos y el auth
def createClient(name, id):
    db = connect()
    data, count = db.table("client").insert({"title": name, "user_id": id}).execute()  # ver como asignar las id
