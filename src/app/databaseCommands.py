from .utils import Connect

connection = Connect()
db = connection.connect()


def db_select(table, columns, equalColumn=False, equalValue=False, setOrder="id", setLimit=None, match=False):
    if match:
        data, count = (db.table(table).
                       select(columns, count='exact').
                       match(match).
                       order(setOrder, desc=True).
                       limit(setLimit).
                       execute())
    elif equalColumn and equalValue:
        data, count = (db.table(table).
                       select(columns, count='exact').
                       eq(equalColumn, equalValue).
                       order(setOrder, desc=True).
                       limit(setLimit).
                       execute())
    else:
        return -1
    # Ver como está compuesta la data y devolverla lo más prolija posible
    try:
        return data[1][0][columns[:-3]], count[1]
    except:
        return data[1], count[1]


def db_update(table, updateDict, equalColumn, equalValue):
    data, count = (db.table(table).
                   update(updateDict, count='exact').
                   eq(equalColumn, equalValue).
                   execute())
    return count[1]


# TODO: Ver como hacer esto más prolijo, si es necesario.
def db_delete(table, equalColumn, equalValue):
    if len(equalColumn) == 2 and len(equalValue) == 2:
        data, count = (db.table(table).
                       delete(count='exact').
                       eq(equalColumn[0], equalValue[0]).
                       eq(equalColumn[1], equalValue[1]).
                       execute())
    else:
        data, count = (db.table(table).
                       delete(count='exact').
                       eq(equalColumn, equalValue).
                       execute())
    return count[1]


def db_insert(table, dataDict):
    data, count = (db.table(table).
                   insert(dataDict).
                   execute())
    return data, count[1]