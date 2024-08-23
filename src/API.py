from fastapi import FastAPI, HTTPException, Security
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
    alarma_detail: list[str] = []
    defrost_status: bool


class ContainerAlarms(BaseModel):
    cont_id: int
    name: str
    alarma: bool
    alarma_detail: list[str] = []
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
    statusList: list[ContainerAlarms] = []


# API CALLS


# TODO: Ver los permisos SSL en la db, actualmente no funciona este comando (ver si ya arreglé esto)
@app.delete("/cont/delete/{cont_id}", name="Desvincular contenedor", tags=["Container"],
            description="Elimina todas sus señales y relaciones de un contenedor.\n"
                        "Mucho cuidado usando esto. Solo se pueden eliminar los contenedores enlazados a su cuenta.")
def delete_cont(
        cont_id: int | None = None,
        auth_result: str = Security(auth.verify)
        # auth_result: str = Security(auth.verify, scopes=['mod:cont'])
):
    # TODO: Este comando tiene que desvincular el usuario actual del contenedor. No puede eliminar el contenedor en
    # su totalidad, ni desvincularlo de otros usuarios. No debería borrar sus señales tampoco entonces.
    if requests.check_ownership(auth_result["sub"], cont_id):
        if cont_id:
            results = requests.unlink_cont(auth_result["sub"], cont_id)
            if not results[0]:
                raise HTTPException(status_code=404, detail="No se encontró el contenedor")
            else:
                return {"association_deleted": results[0], "signals_deleted": results[1]}
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


@app.post("/cont/link/", name="Vincular contenedor a un usuario", tags=["Container"],
          description="Vincula un contenedor a un usuario. Ambos deben existir para hacer esto.\n"
                      "En la base de datos está el id y la contraseña del contenedor. Deben ingresarse ambos "
                      "para poder registrar un contenedor a un usuario.\nEl mismo contenedor puede estar asignado "
                      "a multiples usuarios, si estos tienen acceso a las credenciales.")
def link_cont(
        cont_id: int,
        password: str,
        user_id: str | None = None,
        auth_result: str = Security(auth.verify)
        # auth_result: str = Security(auth.verify, scopes=['add:vigia'])
):
    # Multiples usuarios se pueden vincular al mismo contenedor. Primero checkeamos la contraseña
    checkPassword = requests.check_cont_password(cont_id, password)
    if checkPassword == 0:
        raise HTTPException(status_code=404, detail="El contenedor ingresado no existe.")
    elif checkPassword == -1:
        raise HTTPException(status_code=400, detail="La contraseña es incorrecta. Intentelo de nuevo.")
    response = requests.link_cont_to_client(cont_id, user_id if user_id else auth_result["sub"])
    if response == -1:
        raise HTTPException(status_code=404, detail="No se encontró el usuario.")
    if response == -2:
        raise HTTPException(status_code=400, detail="Este contenedor ya está asignado al usuario.")
    return {"status": "Se vinculó el contenedor correctamente"}


@app.get("/client/status/", name="Estado contenedores de un cliente", tags=["Client"],
         description="Devuelve el estado de todos los contenedores de un cliente.\n"
                     "Por defecto devuelve los contenedores asociados al usuario registrado, pero se puede"
                     "especificar uno diferente. Si se hace, ese va a tener prioridad.\n"
                     "También puede devolver los vigias asociados a cada contenedor. En ese caso se puede desactivar "
                     "mostrar su estado si es necesario.")
def get_status(
        user_id: str | None = None,
        auth_result: str = Security(auth.verify)
):
    # Si se ingresa un usuario específico va a tener prioridad este,
    # si no se usa el usuario de la cuenta que hace el request
    response = requests.status_cont_client(user_id if user_id else auth_result["sub"])
    if not response:
        raise HTTPException(status_code=404, detail="No se encontró el cliente.")
    results = StatusList()
    for i, container in enumerate(response):
        currentContainer = ContainerAlarms(
            cont_id=container["id"],
            name=container["name"],
            alarma=True if container["alarm_list"] else False,
            alarma_detail=container["alarm_list"],
            defrost_status=container["defrost_status"],
        )
        results.statusList.append(currentContainer)
    if response:
        return results
    else:
        raise HTTPException(status_code=404, detail="No hay contenedores asignados al usuario.")


# No creo que sea necesario incrementar los permisos de este comando, ya que solo crea una cuenta usando las
# credenciales que se usaron para logguearse. Asi que no se deberían poder crear cuentas ilegítimas.
@app.post("/client/create/{name}", name="Crear cliente", tags=["Client"],
          description="Registra un cliente en la base de datos cuando se loggea por primera vez.\n"
                      "Se debe ingresar un nombre, y este debe ser único entre todos los usuarios."
                      "Este nombre va a ser usado como identificador para enlazar al usuario a un contenedor.")
def create_client(
        name: str,
        auth_result: str = Security(auth.verify),
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
         description="Se usa para verificar si un usuario existe.\n"
                     "Por defecto se usa el de la cuenta, pero se puede especificar uno si es necesario.")
def check_client(
        auth_result: str = Security(auth.verify),
        user_id: str | None = None
):
    # Tiene prioridad el usuario que hace el request, pero se puede especificar otro
    response = requests.check_client_exists(clientID=user_id if user_id else auth_result["sub"])
    if response == -1:
        raise HTTPException(status_code=404, detail="El usuario ingresado no existe.")
    # Ver como devolver los permisos
    return {"status": "El usuario existe", "name": response["name"]}


# TODO: Cambiar esto para que sea un comando de usuario, y se utilice para ver el estado completo de un contenedor
# en particular, asi esa info se entrega por demanda.
# En este caso, no deberia ser necesario que devuelva los clientes vinculados. Podria poner un comando aparte para ello.
@app.get("/admin/status/{cont_id}", name="Estado contenedor", tags=["Container"],
         description="Devuelve el estado de un contenedor especifico. Solo devuelve el estado "
                     "de los contenedores pertenecientes al usuario.\n"
                     "Se puede usar el detailed_alarm para ver que alarmas saltan en especifico.")
def status_cont(cont_id: int | None = None,
                detailed_alarm: bool | None = True,
                auth_result: str = Security(auth.verify)
                ):
    if requests.check_ownership(auth_result["sub"],cont_id):
        status = requests.cont_status(cont_id, detail=True)
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        contStatus = Container(
            cont_id=status["id"],
            name=status["name"],
            temp=status["temp"],
            defrost=False if status["defrost"] is None else status["defrost"],
            arranque_comp=False if status["arranque_comp"] is None else status["arranque_comp"],
            bateria=False if status["bateria"] is None else status["bateria"],
            alarma=True if status["alarm_list"] else False,
            alarma_detail=status["alarm_list"] if detailed_alarm else None,
            defrost_status=status["defrost_status"],
        )
        return contStatus
    else:
        raise HTTPException(status_code=403, detail="Solo el dueño pero ver el estado de su contenedor.")

# COMANDOS DE ADMIN

# TODO: Configurar que solo tenga permiso de ejecución de Admin
@app.post("/cont/create/{cont_id}", name="Crear contenedor", tags=["Admin"],
          description="Crea todas las relaciones de un contenedor. El comando no vincula a un usuario, y este  "
                      "se usa para ingresar los datos de nuevas placas. Luego se pueden vincular usuarios.\n")
def create_cont(
        cont_id: int,
        password: str,
        name: str | None = None,
        configName: str | None = "default",
        auth_result: str = Security(auth.verify)  # Debería tener scope de admin
):
    # Vamos a crear el contenedor sin clientes asociados.
    response = requests.new_cont(cont_id, name, password, configName)
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    return {"status": "El contenedor fue creado con éxito.", "data": response}
