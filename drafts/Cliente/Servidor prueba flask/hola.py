# coding: utf-8 
from flask import Flask, jsonify, abort, make_response, request, json#importa una clase que se llama flask
from flask_cors import CORS
import random
app = Flask(__name__) #a esta aplicacion hay que pasarle como parametro el nombre del modulo que está en la variable _name_ si lo lanzas desde linea de comandos tendrá _main_
CORS(app)


    
   
  
           # Inicialmente vacía
@app.route("/") #esto es un decorador, asocia esta función con la ruta que es una url
def saludar():
    temperaturas = { 'temperatura1': random.uniform(0,50)}
    print (type(json.dumps(temperaturas)))
    return json.dumps(temperaturas)

app.run(host="0.0.0.0") #bucle de eventos.