from datetime import datetime
import jwt


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