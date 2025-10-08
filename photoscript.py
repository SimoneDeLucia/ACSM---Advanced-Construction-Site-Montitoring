from merakiSensors import sensors
import time
import datetime


def photoscript(frequency):
    print("foto in corso")
    sensor_instance.SENSE_photo_all_net()
    print("foto scattate")
    time.sleep(frequency)
    now = datetime.datetime.now()
    if now.hour >= 20:
        return 1
    else:
        return 0


def main():
    while True :
        photoscript(frequency=30)

sensor_instance = sensors()
sensor_instance.__init__()
main()

