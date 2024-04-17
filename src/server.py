import uvicorn

#Inicializamos el servidor
if __name__ == "__main__":
    uvicorn.run("API:app", port=8086, log_level="info") #Remover el reload/Conf mas a fondo