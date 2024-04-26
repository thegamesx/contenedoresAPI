import uvicorn

#Inicializamos el servidor
if __name__ == "__main__":
    uvicorn.run("API:app", port=3000, log_level="info") #Remover el reload/Conf mas a fondo