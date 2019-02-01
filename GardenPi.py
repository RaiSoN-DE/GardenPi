#!/usr/bin/python
# encoding: utf-8

# GardenPi
#
# Copyright (C) 2018 @Max Eric Behr
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# required libraries
import RPi.GPIO as GPIO
import time
import Adafruit_DHT
import lcddriver
from MCP3008 import MCP3008
import SDL_DS1307
import datetime
import requests
import json
import sys
import urllib2
from colorama import *
init(autoreset=True)

SETTINGS = {
    "LIGHT_GPIO":        17,                     # GPIO Number (BCM) for the Relay
    "LIGHT_FROM":        10,                     # from which time the light can be turned on (hour)
    "LIGHT_UNTIL":       21,                     # until which time (hour)
    "LIGHT_SENSOR_GPIO": 19,                     # GPIO Number (BCM) of the light sensor
    "DHT_GPIO":          27,                     # GPIO Number (BCM) of the DHT Sensor
    "DHT_SENSOR":        Adafruit_DHT.DHT22,     # DHT11 or DHT22
    "TEMP_THRESHOLD":    23.0,                   # in Celcius. Above this value, the window will be opened by the servo
    "SERVO_GPIO":        16,                     # GPIO Number (BCM), which opens the window
    "SERVO_OPEN_ANGLE":  90.0,                   # degree, how much the servo will open the window
    "PLANTS": [
        {
            "NAME":                     "Tomaten",
            "GIESOMAT_GPIO":            21,     # GPIO Number (BCM) for the Gies-o-mat Sensor
            "SAMPLE_RATE":              20,     # Sample rate
            "REFRESH_RATE":             1000.0, # Refresh rate in ms
            "GIESOMAT_THRESHOLD":       40,     # if the Threshold of the Sensor is higher than the pump will turn on
            "WATER_PUMP_GPIO":          23,     # GPIO Number (BCM) for the Relay with the pump
            "WATERING_TIME":            10      # the time how long its watering
        },
    ]
}

def readFreq():
	print(Fore.YELLOW + "[!] Misst die Frequenz...")
        start = time.time()
        for plantObject in SETTINGS["PLANTS"]:
                GPIO.setup(plantObject["GIESOMAT_GPIO"], GPIO.IN)
                for impuls_count in range(plantObject["SAMPLE_RATE"]):
		    time.sleep(0.01)
                    GPIO.wait_for_edge(plantObject["GIESOMAT_GPIO"], GPIO.FALLING)
                duration = time.time() - start      #seconds to run for loop
                frequency = plantObject["SAMPLE_RATE"] / duration   #in Hz
                print(Fore.GREEN + "[" + u'\u2713' + "] Gemessene Frequenz = %.1f Hz" % frequency)
                return frequency

def wateringPlants():
    freq = readFreq()
    print(freq)
    for plantObject in SETTINGS["PLANTS"]:
        if freq >= plantObject["GIESOMAT_THRESHOLD"]:
            GPIO.setup(plantObject["WATER_PUMP_GPIO"], GPIO.OUT, initial=GPIO.LOW)
            time.sleep(plantObject["WATERING_TIME"])
            GPIO.output(plantObject["WATER_PUMP_GPIO"], GPIO.HIGH)
            print(Fore.GREEN + "[" + u'\u2713' + "] Pflanzen wurden gegossen")

        elif freq <= plantObject["GIESOMAT_THRESHOLD"]:
            print(Fore.YELLOW + "[!] Pflanzen haben genug Wasser")

def readTime():
    print(Fore.YELLOW + "[!] Liest die Uhrzeit...")
    now = datetime.datetime.now()
    time = now.hour
    print(Fore.GREEN + "[" + u'\u2713' + "] Aktuelle Uhrzeit: " + str(now) + " -> " + str(time))
    return time

def checkLight():
    print(Fore.YELLOW + "[!] Checkt das Licht...")
    timestamp = readTime()
    GPIO.setup(SETTINGS["LIGHT_SENSOR_GPIO"], GPIO.IN)

    if SETTINGS["LIGHT_FROM"] <= timestamp <= SETTINGS["LIGHT_UNTIL"]:
        # check light sensors
        # read 10 times to avoid measuring errors
        value = GPIO.input(SETTINGS["LIGHT_SENSOR_GPIO"])

        if value == 1 :
            # turn light on
            GPIO.setup(SETTINGS["LIGHT_GPIO"], GPIO.OUT, initial=GPIO.LOW) # Relay LOW = ON
	    print(Fore.GREEN + "[" + u'\u2713' + "] Licht wurde ANgeschalten!")
        else:
            # turn light off
            GPIO.setup(SETTINGS["LIGHT_GPIO"], GPIO.OUT, initial=GPIO.HIGH)
	    print(Fore.GREEN + "[" + u'\u2713' + "] Licht wurde AUSgeschalten!")
    else:
        print(Fore.YELLOW + "[!] Zu dieser Uhrzeit wird das Licht nicht eingeschaltet!")
        # turn light off
        GPIO.setup(SETTINGS["LIGHT_GPIO"], GPIO.OUT, initial=GPIO.HIGH)

def checkWeather():
    print(Fore.YELLOW + "[!] Liest das Wetter...")
    api_adress = 'https://api.openweathermap.org/data/2.5/weather?appid=4088ab5dba5794ba1d3a631eb503966a&q=Neubrandenburg'

    json_data = requests.get(api_adress).json()

    url = urllib2.urlopen(api_adress)
    obj = json.load(url)

    weather = obj["weather"][0]["main"]

    if weather == "Rain":
        rain = True
    else:
        rain = False
    print(Fore.GREEN + "[" + u'\u2713' + "]" " Regen: " + str(rain))
    return rain # Return a Boolean: True = Rain False = No Rain

def checkWindow():
    rain = checkWeather()
    # read temperature
    print(Fore.YELLOW + "[!] Misst die Temperatur...")
    humidity, temperature = Adafruit_DHT.read_retry(SETTINGS["DHT_SENSOR"], SETTINGS["DHT_GPIO"])
    print(Fore.GREEN + "[" + u'\u2713' + "] Temperatur: " + str(round(temperature)) + "^C")
    GPIO.setup(SETTINGS["SERVO_GPIO"], GPIO.OUT)
    pwm = GPIO.PWM(SETTINGS["SERVO_GPIO"], 50)

    if temperature > SETTINGS["TEMP_THRESHOLD"] and rain == False:
        # open window
        pwm.start(2.5)
        pwm.ChangeDutyCycle(5)
        pwm.stop()
	print(Fore.GREEN + "[" + u'\u2713' + "] " + "Fenster wurde geoeffnet!")
    else:
        # close window
        pwm.start(2.5)
	print(Fore.GREEN + "[" + u'\u2713' + "] " "Fenster wurde geschlossen")
    # save current
    time.sleep(2)
    pwm.ChangeDutyCycle(0)

def lcdInfo():
    print(Fore.YELLOW + "[!] Checkt LCD Display...")
    lcd = lcddriver.lcd()
    time = datetime.datetime.now()
	
    lcd.lcd_backlight("off")
    lcd.lcd_clear()
    lcd.lcd_display_string("     GreenPi    ", 1)
    lcd.lcd_display_string(str(time), 2)
    print(Fore.GREEN + "[" + u'\u2713' + "] LCD Display aktualisiert!")

if __name__ == '__main__':
    try:
      while True:
	sys.getdefaultencoding()

        print(Fore.GREEN + "          ____               _            ____  _ ")
        print(Fore.GREEN + "         / ___| __ _ _ __ __| | ___ _ __ |  _ \(_)")
        print(Fore.GREEN + "        | |  _ / _` | '__/ _` |/ _ \ '_ \| |_) | |")
        print(Fore.GREEN + "        | |_| | (_| | | | (_| |  __/ | | |  __/| |")
        print(Fore.GREEN + "         \____|\__,_|_|  \__,_|\___|_| |_|_|   |_|")
	print("                " + Back.GREEN + Fore.BLACK + Style.BRIGHT +" SMART GRENNHOUSE CONTROL ")
	print(Fore.YELLOW + Style.BRIGHT + "******************** GardenPi gestartet ********************")
	print(Fore.YELLOW + Style.BRIGHT + "*        Mit CTRL + C kannst du das Programm beenden       *")
	print(Fore.YELLOW + Style.BRIGHT + "*	            Version 1.0 Alpha                      *")
	print(Fore.YELLOW + Style.BRIGHT + "*               (C)opyright by Max Eric Behr               *")
	print(Fore.YELLOW + Style.BRIGHT + "************************************************************")
        # GPIO Stuff
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        # Functions
	readFreq()
        # wateringPlants()
        # checkWeather()
        checkLight()
        checkWindow()
	lcdInfo()
        print(Fore.YELLOW + Style.BRIGHT + "********************* GardenPi beendet *********************")
	print("Wartet jetzt 20 Sekunden...")
        time.sleep(20)
# Reset on CTRL+C
    except KeyboardInterrupt:
        print(Fore.RED + Style.BRIGHT + "Du hast CTRL + C gedrückt. Das Programm wird nun beendet...")
        GPIO.cleanup()
	print(Fore.RED + Style.BRIGHT + "******************** GardenPi gestoppt ********************")
