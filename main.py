import uvicorn

#Inicializamos el servidor
if __name__ == "__main__":
    uvicorn.run("server:app", port=8086, log_level="info") #Remover el reload/Conf mas a fondo