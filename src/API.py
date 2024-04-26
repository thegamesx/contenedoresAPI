from fastapi import FastAPI, HTTPException, Query, Security
from fastapi.middleware.cors import CORSMiddleware
from typing_extensions import Annotated
from pydantic import BaseModel
import app.requests as requests
from src.app.utils import VerifyToken
from src.app.config import get_metadata


# CONFIGURACIÓN


app = FastAPI(openapi_tags=get_metadata())
auth = VerifyToken()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)


# CLASES


class Container(BaseModel):
    cont_id: int
    name: str
    temp: float
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


class StatusList(BaseModel):
    statusList: list[ContStatus] = []


# TEST COMMANDS

@app.get("/test/public", name="Test public permission")
def public():
    return {"message": "Este mensaje es publico y accesible por cualquiera."}


@app.get("/test/protected", name="Test public permission")
def protected(auth_result: str = Security(auth.verify)):
    return {"message": "Este mensaje esta protegido y solo es accesible por usuarios registrados.",
            "returns": auth_result}


@app.get("/test/admin", name="Test public permission")
def admin(auth_result: str = Security(auth.verify, scopes=['read:messages'])):
    return {"message": "Este mensaje es solo para administradores.",
            "returns": auth_result}


# API CALLS


@app.post("/cont/create/{cont_id}", name="Crear contenedor", tags=["Container"],
          description="Crea todas las relaciones de un contenedor. Debe proveerse un cliente para vincular, "
                      "pero luego se pueden vincular nuevos o modificarlos.")
def create_cont(cont_id: int | None = None, client_id: int | None = None, name: str | None = None):
    # Primero nos fijamos si el cliente existe
    response = requests.new_cont(client_id, cont_id, name)
    if response == -1:
        raise HTTPException(status_code=400, detail="El contenedor ingresado ya existe.")
    if response == -2:
        raise HTTPException(status_code=404, detail="No se encontró el cliente")
    return {"status": "El contenedor fue creado con éxito."}


@app.get("/cont/status/{cont_id}", name="Estado contenedor", tags=["Container"],
         description="Devuelve el estado de un contenedor especifico. Normalmente se usa el de clientes, "
                     "pero si se necesita solo ver el estado de un contenedor especifico se puede usar este.\n"
                     "También sirve para ver que clientes tiene asociado.")
def status_cont(cont_id: int | None = None,
                show_status: bool | None = True,
                show_vigias: bool | None = True):
    status = requests.cont_status(cont_id)
    if status == -1:
        raise HTTPException(status_code=404, detail="No se encontró el contenedor")
    if not show_status and not show_vigias:
        raise HTTPException(status_code=400, detail="No hay información para mostrar")
    clients = requests.cont_assigned(status["idvigia"])
    if show_status:
        contStatus = Container(
            cont_id=status["id"],
            name=status["name"],
            temp=status["temp"],
            defrost=False if status["defrost"] is None else status["defrost"],
            arranque_comp=False if status["arranque_comp"] is None else status["arranque_comp"],
            bateria=False if status["bateria"] is None else status["bateria"],
            alarma=status["alarma"],
            defrost_status=status["defrost_status"],
        )
    else:
        contStatus = "No info"
    if clients:
        if show_vigias:
            clientList = []
            for client in clients:
                clientList.append(Client(
                    name=client["title"],
                    id=client["user_id"]
                ))
            if show_status:
                result = ContStatus(
                    status=contStatus,
                    clients=clientList
                )
            else:
                result = clientList
            return result
        else:
            return contStatus
    else:
        return {"warning": "El contenedor no tiene clientes asociados", "status": contStatus}


@app.delete("/cont/delete/{cont_id}", name="Eliminar contenedor", tags=["Container"],
            description="Elimina un contenedor, incluyendo todas sus señales y configuraciones.\n"
                        "Mucho cuidado usando esto.")
def delete_cont(cont_id: int | None = None):
    if cont_id:
        results = requests.del_cont(cont_id)
        if results[0] == 0 and results[1] == 0:
            raise HTTPException(status_code=404, detail="No se encontró el contenedor")
        else:
            return {"associations_deleted": results[0], "config_deleted": results[1], "signals_deleted": results[2]}
    else:
        raise HTTPException(status_code=400, detail="No se ingresó un numero de contenedor")


# Cambiar este comando, hacerlo más simple.
@app.put("/cont/update/", name="Modificar contenedor", tags=["Container"],
         description="Actualiza el nombre de un contenedor en particular. "
                     "Esto solo lo puede realizar el dueño del mismo.")
def update_cont(
        cont_id: int | None = None,
        display_name: str | None = None,
):
    assign_request = {}
    if cont_id:
        # Checkear permisos antes de hacer el cambio.
        if display_name:
            assign_request["name_status"] = requests.name_cont(cont_id, display_name)
            if assign_request["name_status"] == 0:
                raise HTTPException(status_code=404, detail="No se encontró el contenedor.")
            if assign_request["name_status"] == -1:
                raise HTTPException(status_code=422,
                                    detail="Ocurrió un error inesperado. Contacte al administrador del sistema.")
        else:
            raise HTTPException(status_code=400, detail="El nombre no puede estar vacío.")
    else:
        raise HTTPException(status_code=400, detail="Se debe ingresar el id de un contenedor.")


@app.post("/cont/link/", name="Vincular contenedor a un vigia", tags=["Container"],
          description="Vincula un contenedor a un vigia. Ambos deben existir para hacer esto, "
                      "sino puede usar el comando de crear contenedor.")
def link_cont(cont_id: int, client_id: int):
    response = requests.link_cont_to_client(cont_id, client_id)
    if response == -1:
        raise HTTPException(status_code=404, detail="No se encontró el usuario.")
    if response == -2:
        raise HTTPException(status_code=404, detail="No se encontró el contenedor.")
    if response == -3:
        raise HTTPException(status_code=400, detail="Este contenedor ya está asignado al vigia.")
    return {"status": "Se vinculó el contenedor correctamente"}


# TODO: Ver bien los errores
@app.get("/client/status/{client_id}", name="Estado contenedores de un cliente", tags=["Client"],
         description="Devuelve el estado de todos los contenedores de un cliente.\n"
                     "También puede devolver los vigias asociados a cada contenedor. En ese caso se puede desactivar "
                     "mostrar su estado si es necesario.")
def get_status(
        client_id: int,
        return_status: bool | None = True,
        return_vigias: bool | None = False
):
    contStatus = requests.status_cont_client(client_id)
    if contStatus == -1:
        raise HTTPException(status_code=404, detail="No se encontró el cliente.")
    if return_vigias:
        results = StatusList()
    else:
        results = ContainerList()
    for i, container in enumerate(contStatus):
        if container != -1:
            currentContainer = Container(
                cont_id=container["id"],
                name=container["name"],
                temp=container["temp"],
                defrost=False if container["defrost"] is None else container["defrost"],
                arranque_comp=False if container["arranque_comp"] is None else container["arranque_comp"],
                bateria=False if container["bateria"] is None else container["bateria"],
                alarma=container["alarma"],
                defrost_status=container["defrost_status"],
            )
            if return_vigias:
                clients = requests.cont_assigned(container["idvigia"])
                clientList = []
                for client in clients:
                    clientList.append(Client(
                        name=client["title"],
                        id=client["user_id"]
                    ))
                contWithVigias = ContStatus(
                    status=currentContainer,
                    clients=clientList
                )
                results.statusList.append(contWithVigias)
            else:
                results.contList.append(currentContainer)
    return {"status": results}


# Asignar permisos de admin para usar este comando. Crea clientes nuevos
@app.post("/client/create/", name="Crear cliente", tags=["Client"],
          description="Crea un cliente nuevo. Requiere permisos de admin.\n"
                      "Temporal: Se ingresa el ID manualmente. Cambiar luego")
def create_client(client_name: Annotated[str, Query(min_length=1)], client_id: int):
    response = requests.create_new_client(client_name, client_id)
    return {"status": response}
