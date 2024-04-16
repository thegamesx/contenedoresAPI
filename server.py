from typing import Union
from fastapi import FastAPI, HTTPException, Query
from typing_extensions import Annotated
from pydantic import BaseModel
import dbRequests

tags_metadata = [
    {
        "name": "Container",
    },
    {
        "name": "Client"
    }
]

app = FastAPI(openapi_tags=tags_metadata)


# CONTENEDORES


class Container(BaseModel):
    cont_id: int
    name: str
    temp: float
    compresor: bool
    evaporacion: bool
    defrost: bool
    arranque_comp: bool
    bateria: bool
    alarma: bool
    defrost_status: bool


class Client(BaseModel):
    name: str
    id: int


class ContainerList(BaseModel):
    contList: list[Container] = []


class ContStatus(BaseModel):
    status: Container
    clients: list[Client] = []


@app.post("/cont/create/{cont_id}", name="Crear contenedor", tags=["Container"],
          description="Crea todas las relaciones de un contenedor. Debe proveerse un cliente para vincular, "
                      "pero luego se pueden vincular nuevos o modificarlos.")
def create_cont(cont_id: int | None = None, client_id: int | None = None, name: str | None = None):
    # Primero nos fijamos si el cliente existe
    response = dbRequests.new_cont(client_id, cont_id, name)
    if response == -1:
        raise HTTPException(status_code=400, detail="El contenedor ingresado ya existe.")
    if response == -2:
        raise HTTPException(status_code=404, detail="No se encontró el cliente")
    return {"status": "El contenedor fue creado con éxito."}


@app.get("/cont/status/{cont_id}", name="Estado contenedor", tags=["Container"],
         description="Devuelve el estado de un contenedor especifico. Normalmente se usa el de clientes, "
                     "pero si se necesita solo ver el estado de un contenedor especifico se puede usar este.\n"
                     "También sirve para ver que clientes tiene asociado.")
def status_cont(cont_id: int | None = None):
    status = dbRequests.cont_status(cont_id)
    if status == -1:
        raise HTTPException(status_code=404, detail="No se encontró el contenedor")
    clients = dbRequests.cont_assigned(status["idvigia"])
    # Ver que pasa si el contenedor no tiene clientes asignados.
    contStatus = Container(
            cont_id=status["id"],
            name=status["name"],
            temp=status["temp"],
            compresor=status["compresor"],
            evaporacion=status["evaporacion"],
            defrost=status["defrost"],
            arranque_comp=status["arranque_comp"],
            bateria=status["bateria"],
            alarma=status["alarma"],
            defrost_status=status["defrost_status"],
        )
    clientList = []
    for client in clients:
        clientList.append(Client(
            name=client["title"],
            id=client["user_id"]
        ))
    result = ContStatus(
        status=contStatus,
        clients=clientList
    )
    return result


@app.delete("/cont/delete/{cont_id}", name="Eliminar contenedor", tags=["Container"],
            description="Elimina un contenedor, incluyendo todas sus señales y configuraciones.\n"
                        "Mucho cuidado usando esto.")
def delete_cont(cont_id: int | None = None):
    if cont_id:
        results = dbRequests.del_cont(cont_id)
        if results[0] == 0 and results[1] == 0:
            raise HTTPException(status_code=404, detail="No se encontró el contenedor")
        else:
            return {"associations_deleted": results[0], "signals_deleted": results[1]}
    else:
        raise HTTPException(status_code=400, detail="No se ingresó un numero de contenedor")


@app.put("/cont/update/", name="Modificar contenedor", tags=["Container"],
         description="Actualiza un contenedor en particular. Los datos que se pueden cambiar son:\n"
                     "- Vincular a un cliente nuevo\n"
                     "- Actualizar el nombre\n"
                     "- Limpiar historial de señales")
def update_cont(
        cont_id: int | None = None,
        client_id: int | None = None,
        display_name: str | None = None,
        clear_history: bool | None = False
):
    assign_request = {}
    if cont_id:
        if client_id:
            assign_request["link_status"] = dbRequests.assign_cont(client_id, cont_id, display_name)
            if assign_request["link_status"] == -1:
                raise HTTPException(status_code=400, detail="El cliente ya tiene asignado ese contenedor.")
        if display_name:
            assign_request["name_status"] = dbRequests.name_cont(cont_id, display_name)
            if assign_request["name_status"] == 0:
                raise HTTPException(status_code=404, detail="No se encontró el contenedor.")
            if assign_request["name_status"] == -1:
                raise HTTPException(status_code=422,
                                    detail="Ocurrió un error inesperado. Contacte al administrador del sistema.")
        if clear_history:
            assign_request["history_rows_deleted"] = dbRequests.clear_history(cont_id)
        if assign_request == {}:
            raise HTTPException(status_code=400, detail="No se realizaron cambios, revise los datos ingresados.")
        else:
            return assign_request
    else:
        return {"status": "Se debe ingresar el id de un contenedor."}


@app.get("/client/status/{client_id}", name="Estado contenedores de un cliente", tags=["Client"],
         description="Devuelve el estado de todos los contenedores de un cliente.")
def get_status(client_id: int):
    contStatus = dbRequests.status_cont_client(client_id)
    results = ContainerList()
    for i, container in enumerate(contStatus):
        currentContainer = Container(
            cont_id=container["id"],
            name=container["name"],
            temp=container["temp"],
            compresor=container["compresor"],
            evaporacion=container["evaporacion"],
            defrost=container["defrost"],
            arranque_comp=container["arranque_comp"],
            bateria=container["bateria"],
            alarma=container["alarma"],
            defrost_status=container["defrost_status"],
        )
        results.contList.append(currentContainer)
    return {"status": results}


# Asignar permisos de admin para usar este comando. Crea clientes nuevos
@app.post("/client/create/", name="Crear cliente", tags=["Client"],
          description="Crea un cliente nuevo. Requiere permisos de admin.\n"
                      "Temporal: Se ingresa el ID manualmente. Cambiar luego")
def create_client(client_name: Annotated[str, Query(min_length=1)], client_id: int):
    response = dbRequests.create_new_client(client_name, client_id)
    return {"status": response}
