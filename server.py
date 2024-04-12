from typing import Union
from fastapi import FastAPI, HTTPException, Query
from typing_extensions import Annotated
from pydantic import BaseModel
import dbRequests

app = FastAPI()

"""
class Item(BaseModel):
    name: str
    price: float
    is_offer: Union[bool, None] = None


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_name": item.name, "item_id": item_id}
"""


# Mi codigo, borrar lo de arriba luego

# CONTENEDORES

@app.get("/cont/status/{cont_id}", name="Estado contenedor",
         description="Devuelve el estado de un contenedor especifico. Normalmente se usa el de clientes, "
                     "pero si se necesita solo ver el estado de un contenedor especifico se puede usar este.")
def status_cont(cont_id: int | None = None):
    results = dbRequests.cont_status(cont_id)
    if results == -1:
        raise HTTPException(status_code=404, detail="No se encontró el contenedor")
    else:
        return results


@app.delete("/cont/delete/{cont_id}", name="Eliminar contenedor",
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


@app.put("/cont/update/", name="Modificar contenedor",
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
    if cont_id:
        if client_id:
            assign_request = dbRequests.assign_cont(client_id, cont_id, display_name)
            if assign_request == -1:
                raise HTTPException(status_code=400, detail="El cliente ya tiene asignado ese contenedor.")
            if display_name:
                assign_request = dbRequests.name_cont(cont_id, client_id, display_name)
                if assign_request == 0:
                    raise HTTPException(status_code=404, detail="No se encontró el contenedor.")
        if clear_history:
            assign_request = dbRequests.clear_history(cont_id)
            return {"rows_deleted": assign_request}  # Cambiar como se devuelve el estado


    else:
        return {"status": "Se debe ingresar el id de un contenedor."}


@app.get("/cont/status/{client_id}", name="Estado contenedores de un cliente",
         description="Devuelve el estado de todos los contenedores de un cliente.")
def get_status(client_id: int):
    contStatus = dbRequests.contStatus(client_id)
    print(contStatus)
    return {"client_id": client_id}  # Acomodar el dict con los datos. Hacer pruebas


# Asignar permisos de admin para usar este comando. Crea clientes nuevos
@app.post("/client/create/", name="Crear cliente",
          description="Crea un cliente nuevo. Requiere ingresar un nombre y permisos de admin.")
def create_client(client_name: Annotated[str, Query(min_length=1)]):
    response = dbRequests.createClient(client_name)
    return {"status": client_name}
