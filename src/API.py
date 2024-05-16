from fastapi import FastAPI, HTTPException, Query, Security
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import app.requests as requests
from app.utils import VerifyToken
from app.config import get_metadata

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
    id: str


class ContainerList(BaseModel):
    contList: list[Container] = []


class ContStatus(BaseModel):
    status: Container
    clients: list[Client] = []


class StatusList(BaseModel):
    statusList: list[ContStatus] = []


# API CALLS


@app.post("/cont/create/{cont_id}", name="Crear contenedor", tags=["Container"],
          description="Crea todas las relaciones de un contenedor. Debe proveerse un cliente para vincular "
                      "(por defecto es la cuenta loggeada), pero luego se pueden vincular nuevos o modificarlos.")
def create_cont(
        cont_id: int | None = None,
        client_id: str | None = None,
        name: str | None = None,
        owner: bool | None = True,  # Vamos a suponer que si alguien registra un contenedor va a ser el dueño.
        auth_result: str = Security(auth.verify)
):
    # El contenedor solo va a ser vinculado si existen señales. Es una forma de verificar que no se ingrese
    # cualquier cosa.
    # Primero nos fijamos si el cliente existe
    if cont_id:
        response = requests.new_cont(client_id if client_id else auth_result["sub"], cont_id, name, owner)
        if response == -1:
            raise HTTPException(status_code=400, detail="El contenedor ingresado ya existe.")
        if response == -2:
            raise HTTPException(status_code=404, detail="No se encontró el cliente.")
        if response == -3:
            raise HTTPException(status_code=403,
                                detail="El contenedor debe estar instalado y funcionando para poder registrarlo.")
        if owner:
            pass  # Cambiar esto una vez que ande la env management api
            # auth.register_owner(client_id if client_id else auth_result["sub"])
    else:
        raise HTTPException(status_code=400, detail="Debe ingresar el ID de un contenedor.")
    return {"status": "El contenedor fue creado con éxito."}


@app.get("/cont/status/{cont_id}", name="Estado contenedor", tags=["Container"],
         description="Devuelve el estado de un contenedor especifico. Normalmente se usa el de clientes, "
                     "pero si se necesita solo ver el estado de un contenedor especifico se puede usar este.\n"
                     "También sirve para ver que clientes tiene asociado.")
def status_cont(cont_id: int | None = None,
                show_status: bool | None = True,
                show_vigias: bool | None = True,  # Esto debería mostrarlo solo si lo está viendo el dueño del cont
                auth_result: str = Security(auth.verify)
                ):
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
            # Vemos los permisos antes de devolver el estado. Solo debería devolverlo si lo está pidiendo el dueño
            # del container, o si es un usuario asignado a él.
            if requests.check_ownership(auth_result["sub"], cont_id):
                clientList = []
                for client in clients:
                    clientList.append(Client(
                        name=client["name"],
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
                raise HTTPException(status_code=403, detail="Solo el dueño pero ver los vigias asociados al contenedor")
        else:
            return contStatus
    else:
        return {"warning": "El contenedor no tiene clientes asociados", "status": contStatus}


# Ver los permisos SSL en la db, actualmente no funciona este comando
@app.delete("/cont/delete/{cont_id}", name="Eliminar contenedor", tags=["Container"],
            description="Elimina un contenedor, incluyendo todas sus señales y configuraciones.\n"
                        "Mucho cuidado usando esto. Requiere ser el dueño.")
def delete_cont(
        cont_id: int | None = None,
        auth_result: str = Security(auth.verify)
        # auth_result: str = Security(auth.verify, scopes=['mod:cont'])
):
    if requests.check_ownership(auth_result["sub"], cont_id):
        if cont_id:
            results = requests.del_cont(cont_id)
            if results[0] == 0 and results[1] == 0:
                raise HTTPException(status_code=404, detail="No se encontró el contenedor")
            else:
                return {"associations_deleted": results[0], "config_deleted": results[1], "signals_deleted": results[2]}
        else:
            raise HTTPException(status_code=400, detail="No se ingresó un numero de contenedor")
    else:
        raise HTTPException(status_code=403, detail="No puede eliminar un contenedor que no le pertenece.")


@app.put("/cont/update/", name="Modificar contenedor", tags=["Container"],
         description="Actualiza el nombre de un contenedor en particular. "
                     "Esto solo lo puede realizar el dueño del mismo.")
def update_cont(
        cont_id: int | None = None,
        display_name: str | None = None,
        auth_result: str = Security(auth.verify)
        #  auth_result: str = Security(auth.verify, scopes=['mod:cont'])
):
    assign_request = {}
    if cont_id:
        # Checkea permisos antes de hacer el cambio.
        if requests.check_ownership(auth_result["sub"], cont_id):
            if display_name:
                assign_request["name_status"] = requests.name_cont(cont_id, display_name)
                if assign_request["name_status"] == 0:
                    raise HTTPException(status_code=404, detail="No se encontró el contenedor.")
                if assign_request["name_status"] == -1:
                    raise HTTPException(status_code=422,
                                        detail="Ocurrió un error inesperado. Contacte al administrador del sistema.")
                return {"status": "El nombre se cambió exitosamente."}
            else:
                raise HTTPException(status_code=400, detail="El nombre no puede estar vacío.")
        else:
            raise HTTPException(status_code=403, detail="Solo el dueño del contenedor puede cambiar su nombre.")
    else:
        raise HTTPException(status_code=403, detail="Se debe ingresar el id de un contenedor.")


@app.post("/cont/link/", name="Vincular contenedor a un vigia", tags=["Container"],
          description="Vincula un contenedor a un vigia. Ambos deben existir para hacer esto, "
                      "sino puede usar el comando de crear contenedor.")
def link_cont(
        cont_id: int,
        vigia_id: str,
        auth_result: str = Security(auth.verify)
        # auth_result: str = Security(auth.verify, scopes=['add:vigia'])
):
    # Solo el dueño del contenedor puede vincular, asi que chequeamos eso primero
    if requests.check_ownership(auth_result["sub"], cont_id):
        response = requests.link_cont_to_client(cont_id, vigia_id)
        if response == -1:
            raise HTTPException(status_code=404, detail="No se encontró el usuario.")
        if response == -2:
            raise HTTPException(status_code=404, detail="No se encontró el contenedor.")
        if response == -3:
            raise HTTPException(status_code=400, detail="Este contenedor ya está asignado al vigia.")
        return {"status": "Se vinculó el contenedor correctamente"}
    else:
        raise HTTPException(status_code=400, detail="No puede vincular un contenedor que no es suyo.")


# TODO: Ver bien los errores
@app.get("/client/status/", name="Estado contenedores de un cliente", tags=["Client"],
         description="Devuelve el estado de todos los contenedores de un cliente.\n"
                     "Por defecto devuelve los contenedores asociados al usuario registrado, pero se puede"
                     "especificar uno diferente. Si se hace, ese va a tener prioridad.\n"
                     "También puede devolver los vigias asociados a cada contenedor. En ese caso se puede desactivar "
                     "mostrar su estado si es necesario.")
def get_status(
        client_id: int | None = None,
        return_status: bool | None = True,
        return_vigias: bool | None = False,
        auth_result: str = Security(auth.verify)
):
    # Si se ingresa un usuario específico va a tener prioridad este,
    # si no se usa el usuario de la cuenta que hace el request
    contStatus = requests.status_cont_client(client_id if client_id else auth_result["sub"])
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
                        name=client["name"],
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


# No creo que sea necesario incrementar los permisos de este comando, ya que solo crea una cuenta usando las
# credenciales que se usaron para logguearse. Asi que no se deberían poder crear cuentas ilegítimas.
@app.post("/client/create/", name="Crear cliente", tags=["Client"],
          description="Registra un cliente en la base de datos cuando se loggea por primera vez.")
def create_client(
        auth_result: str = Security(auth.verify),
        name: str | None = None,
):
    if name:
        checkDuplicate = requests.check_client_exists(username=name)
        if checkDuplicate == -1:
            username = name
        else:
            raise HTTPException(status_code=400, detail=
            "El nombre ingresado ya está siendo usado por otro usuario. Ingrese otro nombre.")
    else:
        raise HTTPException(status_code=400, detail="Se debe ingresar un nombre de usuario.")
    result = requests.create_new_client(username, auth_result["sub"])
    if result == -1:
        raise HTTPException(status_code=400, detail="El usuario ya está registrado en la base de datos.")
    return {"status": "Usuario creado con éxito."}


@app.get("/client/account/", name="Datos de la cuenta", tags=["Client"],
         description="Se usa para verificar si un usuario existe y que permisos tiene.")
def check_client(
        auth_result: str = Security(auth.verify),
        userID: str | None = None
):
    # Tiene prioridad el usuario que hace el request, pero se puede especificar otro
    response = requests.check_client_exists(clientID=userID if userID else auth_result["sub"])
    if response == -1:
        return {"status": "El usuario ingresado no existe."}
    # Ver como devolver los permisos
    return {"status": "El usuario existe", "name": response["name"]}
