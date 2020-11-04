from sense_hat import SenseHat
import time


sense=SenseHat()
#sense.show_message("VERNE A TOPE!!")

while True:
    print("la temperatura es:")
    time_inicio=time.time()
    print (sense.get_temperature())
    orientation = sense.get_orientation()
    pitch = orientation['pitch']
    roll = orientation['roll']
    yaw = orientation['yaw']
    print(pitch, yaw, roll)
    time.sleep(1)


# sense.show_message(format(sense.get_temperature()))
# time_final=time.time()
# time.sleep(0.5)
# print("Tiempo de procesado sensor temperatura:")
# print(time_final-time_inicio)
#
#
# time_inicio=time.time()
# print("la presión es:")
# print(sense.get_pressure())
# time_final=time.time()
# time.sleep(0.5)
# print("Tiempo de procesado sensor presion:")
# print(time_final-time_inicio)
#
# time_inicio=time.time()
# print("la humedad es:")
# print(sense.get_humidity())
# time_final=time.time()
# time.sleep(0.5)
# print("Tiempo de procesado sensor de humedad")
# print(time_final-time_inicio)
