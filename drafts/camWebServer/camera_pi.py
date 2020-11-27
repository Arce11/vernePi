#Generación de la clase Camera que se importará en appCam.py
import time
import io
import threading
import picamera


class Camera(object):
    thread = None  # Hilo que lee frames de la camara
    frame = None  # Para que el hilo almacene el frame actual
    last_access = 0  # Tiempo del último acceso del cliente a la camara

    def initialize(self):
        if Camera.thread is None:
            # Creamos y comenzamos el hilo para leer los frames
            Camera.thread = threading.Thread(target=self._thread)
            Camera.thread.start()

            # esperamos hasta que los frames estén disponibles.
            while self.frame is None:
                time.sleep(0)

    def get_frame(self):
        Camera.last_access = time.time()
        self.initialize()
        return self.frame

    @classmethod
    def _thread(cls):
        with picamera.PiCamera() as camera:
            # configuración de la camara
            camera.resolution = (320, 240)
            camera.hflip = True
            camera.vflip = True

            # previsualización de la camara
            camera.start_preview()
            time.sleep(2)

            stream = io.BytesIO()
            for foo in camera.capture_continuous(stream, 'jpeg',
                                                 use_video_port=True):
                # almacenamos el frame
                stream.seek(0)
                cls.frame = stream.read()

                # reseteamos el stream para el siguiente frame
                stream.seek(0)
                stream.truncate()

                # Si no hay clientes conectados en los últimos 10 segundos
                # paramos el hilo
                if time.time() - cls.last_access > 10:
                    break
        cls.thread = None
