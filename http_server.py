from flask import Flask, render_template, Response, jsonify, request, json
from flask_cors import CORS
import socket
import time
import io
import threading
import picamera

app = Flask(__name__)
CORS(app)

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


# COMMANDS ROUTE
@app.route("/control_remoto", methods=["PUT"])
def json_receive():
    data=request.get_json()
    print("He recibido", data)
    # Local socket to transfer data to the main script
    ser_address = "169.254.30.57"
    puerto = 8000
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # s.connect((ser_address, puerto))
    # JSON -> string -> bytes
    s.sendto(json.dumps(data).encode("utf8"), ('localhost', 8000))
    return jsonify({'data': data}, 200, "Ok")


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera()), mimetype='multipart/x-mixed-replace; boundary=frame')


class Camera(object):
    thread = None
    frame = None  # current frame
    last_access = 0

    def initialize(self):
        if Camera.thread is None:
            Camera.thread = threading.Thread(target=self._thread)
            Camera.thread.start()

            # wait until frames are ready
            while self.frame is None:
                time.sleep(0)

    def get_frame(self):
        Camera.last_access = time.time()
        self.initialize()
        return self.frame

    @classmethod
    def _thread(cls):
        with picamera.PiCamera() as camera:
            # Camera config
            camera.resolution = (400, 300)
            camera.hflip = False
            camera.vflip = False

            camera.start_preview()
            time.sleep(2)

            stream = io.BytesIO()
            for foo in camera.capture_continuous(stream, 'jpeg',
                                                 use_video_port=True):
                # Store the frame
                stream.seek(0)
                cls.frame = stream.read()
                # Reset the stream for next frame
                stream.seek(0)
                stream.truncate()

                # If no clients in 10s, stop the thread
                if time.time() - cls.last_access > 10:
                    break
        cls.thread = None


if __name__ == '__main__':
    app.run(host='0.0.0.0', port =80, debug=True, threaded=True)
