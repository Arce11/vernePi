#Generando un servidor web para streaming con Flask
#En la Raspberry Pi

from flask import Flask, render_template, Response, jsonify, request, json
from flask_cors import CORS
import socket

# Raspberry Pi camera module (requiere el paquete picamera)
from camera_pi import Camera

app = Flask(__name__)
CORS(app)
def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')



@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')


def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# RUTA PARA LOS TELECOMANDOS
@app.route("/control_remoto", methods=["PUT"])
def json_receive():
    data=request.get_json()
    print("He recibido", data)
    # abrimos un socket local para transferir los datos al script
    ser_address = "169.254.30.57"
    puerto = 8000
    S = socket.socket()
    S.connect((ser_address, puerto))
    #convertimos el JSON a un string y lo codificamos en bytes
    #Se ha de convertir a un string para que sea posible realizar la conversion a bytes
    S.send(json.dumps(data).encode("utf8"))
    return jsonify({'data': data}, 200, "Ok")





'''
@app.route('/video_feed')



def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port =80, debug=True, threaded=True)
