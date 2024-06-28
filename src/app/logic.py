import logging
from datetime import datetime


def convert_date(dateStr):
    strippedDate = dateStr[:-6]
    # Se incorporó este try para testear fechas ingresadas manualmente.
    try:
        return datetime.strptime(strippedDate, "%Y-%m-%dT%H:%M:%S.%f")
    except:
        return datetime.strptime(strippedDate, "%Y-%m-%dT%H:%M:%S")


# Verifica que el controlador este mandando señales. Si no mandó una por 35m devuelve un error
def controller_status(lastSignal):
    timeNow = datetime.now()
    logging.info(timeNow)
    lastSignalDT = convert_date(lastSignal)
    logging.info(lastSignalDT)
    timeDelta = timeNow - lastSignalDT
    logging.info(timeDelta)
    if timeDelta.total_seconds() / 60 > 35:
        return True
    else:
        return False


# Comprueba si el defrost o el compresor está en un estado normal. De no ser así, se activa una alarma
# Se manda el campo a checkear en field, y la condición normal en checkIfTrue, ya que son opuestas
def check_hour_status(data, field, checkIfTrue):
    timeNow = datetime.now()
    # TODO: Ver si esto funciona correctamente
    for row in data:
        if row[field] == checkIfTrue:
            return False
        registeredDate = convert_date(row["date"])
        timeDelta = timeNow - registeredDate
        if timeDelta.total_seconds() / 60 > 60:
            return True
