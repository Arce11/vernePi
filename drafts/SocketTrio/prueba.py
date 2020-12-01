import trio
import sys #para capturar el puerto por consola
import os
import time


puerto=8000



async def timer():

    contador=0
    while True:
        
        print("La cuenta es:", contador)
        contador=contador+1
        await trio.sleep(1)

async def peticion(S):
    while True:
        sd,origen= await S.accept()
        respuesta=await sd.recv(1000)
        respuesta=respuesta.decode("utf8")
        print("respuesta del server:", respuesta)
        print("El tipo de la respuesta es:", type(respuesta))
        sd.close()

async def parent():
    #Creamos el socket asíncrono para gestionar la conexión
    S = trio.socket.socket()
    #asociamos con dirección y puerto (8000) definido en una constante
    await S.bind(("", puerto))
    # A la escucha
    S.listen(1)
    print("Empieza ejecucion asincrona")
    #abrimos la guardería
    async with trio.open_nursery() as nursery:
        print("Aqúi esta el relojito")
        nursery.start_soon(timer)
        #le pasamos el socket a la función para que pueda gestionar la transferencia de datos
        print("Aquí está la peticioncita")
        nursery.start_soon(peticion,S)
    S.close()

trio.run(parent)
    