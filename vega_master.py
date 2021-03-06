#vfs

'''
    ==========================================================
    Vega Flight Software, version 0.5
    Copyright (C) 2021 Jack Woodman - All Rights Reserved

    * You may use, distribute and modify this code under the
    * terms of the GNU GPLv3 license.
    ==========================================================
'''

# You're gonna want the bmp_functions stored in the same folder
# https://github.com/jackwoodman/vega/blob/master/bmp_functions.py
import Adafruit_BMP.BMP085 as BMP085
import time
import smbus
from time import sleep
import math
import threading
import serial
import copy
import csv
from picamera import PiCamera


vega_version = 0.5
internal_version = "0.5"

# The following assumes we only have an altimeter. Need to add config file support for dedicated accelerometer

#============RULES============
# 1.) Function descriptions marked  |--- TO BE REMOVED ---| are only used for
#     debug and dev purposes only. They will be archived on final release, so
#     don't call the function anywhere else that is intended for final release.
#=============================


# Look who hasn't learnt his lesson and is using global variables again
global flight_data
global data_store
global configuration
import time

# Configuration Values
RUN_CAMERA = False
COMP_ID = 0

flight_data = {}
test_shit = {}
data_store = []
bmp_sensor = BMP085.BMP085()
receiving_command = True
if RUN_CAMERA:
    onboard_camera = PiCamera()
configuration = {
    "beep_vol" : 5,
    "debug_mode" : True,
    "rocket_data" : ["CALLISTO II", 3.5, 4]
}




#Constants
VIDEO_FILENAME = "vega_onboard"
VIDEO_SAVELOCATION = "/home/pi/Desktop/"
X_OFFSET = 1.42
RAW_AX_OFFSET = 21100
FILE_VARS = ['time','altitude','velocity',
             'mode','gx','gy','gz','ax','ay','az','id']

#MPU6050 Registers
PWR_MGMT_1   = 0x6B
SMPLRT_DIV   = 0x19
CONFIG       = 0x1A
GYRO_CONFIG  = 0x1B
INT_ENABLE   = 0x38
ACCEL_XOUT_H = 0x3B
ACCEL_YOUT_H = 0x3D
ACCEL_ZOUT_H = 0x3F
GYRO_XOUT_H  = 0x43
GYRO_YOUT_H  = 0x45
GYRO_ZOUT_H  = 0x47
bus = smbus.SMBus(1)    # or bus = smbus.SMBus(0) for older version boards
Device_Address = 0x68   # MPU6050 device address



def MPU_Init():
        # Comments to explain this functino are in imutest.py
        bus.write_byte_data(Device_Address, SMPLRT_DIV, 7)
        bus.write_byte_data(Device_Address, PWR_MGMT_1, 1)
        bus.write_byte_data(Device_Address, CONFIG, 0)
        bus.write_byte_data(Device_Address, GYRO_CONFIG, 24)
        bus.write_byte_data(Device_Address, INT_ENABLE, 1)

def read_raw_data(addr):
        # Reads data from addresses of MPU
        high = bus.read_byte_data(Device_Address, addr)
        low = bus.read_byte_data(Device_Address, addr+1)

        #concatenate higher and lower value
        value = ((high << 8) | low)

        #to get signed value from mpu6050
        if(value > 32768):
                value = value - 65536
        return value



def get_temp():
        return bmp_sensor.read_temperature()

def get_press_local():
        return bmp_sensor.read_pressure()

def get_alt():
        return bmp_sensor.read_altitude()

def get_press_sea():
        return bmp_sensor.read_sealevel_pressure()

""" The RPI needs an internet connection to keep time. Since the rocket won't
    be able to keep an internect connection, I'm going to have to make my own
    shitty timer. The issue: I'm going to use multi-threading to do this. Is
    that bad? Very. Will it work?

    UPDATE
    Guess what. I lied. Totally can work on its own, just can't get an accurate start time.
    That was a monumental waste of time. The homemade time functions are saved in the local
    backup of vega in case I'm wrong twice over.

    DOUBLE UPDATE
    I think I deleted the local backup of vega. There's a chance Time Machine
    has a backup from when it was being worked on on the Mac but otherwise
    the homemade time functions are gone. Good riddence.
    """


global error_log
global flight_log

error_log, flight_log = [], []


def file_append(target_file, data):
    # VFS File Appending Tool
    opened_file = open(target_file, "a")
    opened_file.write(data + "\n")
    opened_file.close()

def file_init(target_file, title):
    # VFS File Creation Tool
    top_line = f"========== {title} ==========\n"
    bottom_line = "=" * (len(top_line)-1) + "\n"
    new_file = open(target_file, "w")
    new_file.write(top_line)
    new_file.write("VEGA v" + str(vega_version)+"\n")
    new_file.write(bottom_line)
    new_file.write(" \n")
    new_file.close()

def flight_log_unload(flight_log, done=True):
    # VFS Flight Log Unloader Tool
    flight_log_title = "vega_flightlog.txt"
    file_init(flight_log_title, "VEGA FLIGHT LOG")
    log_file = open(flight_log_title, "a")

    for tuple in flight_log:
        log, timestamp = tuple
        log_file.write(f"- {timestamp} : {log}\n")

    if done:
        log_file.write("END OF LOG\n")
    log_file.close()

def error_unload(error_list):
    error_log_title = "vega_errorlog.txt"
    file_init(error_log_title, "VEGA ERROR LOG")

    error_file = open(error_log_title, "a")

    for tuple in error_list:
        error, timestamp = tuple
        error_file.write(f"- {timestamp} : {error}\n")

    error_file.close()

def data_unload(data_output, variable_list=FILE_VARS):
    #Creates a new csv file and stores the input within


    with open('flight_data.csv', 'w', newline='') as file:

        # Initialise csv writer
        writer = csv.writer(file)

        # Write header line with column names
        writer.writerow(variable_list)

        # For every packet in the input, compile and write a line
        # to the csv file

        for entry in data_output:

            new_line = []

            # Build list of gyro and acc values from input
            gyro_vals = [entry[4]["Gx"], entry[4]["Gy"], entry[4]["Gz"]]
            acel_vals = [entry[5]["Ax"], entry[5]["Ay"], entry[5]["Az"]]



            # Add first unlisted variables
            for first in range(4):
                new_line.append(str(entry[first]))

            # Add gyoscope measurments
            for g_index in range(3):
                new_line.append(gyro_vals[g_index])

            # Add accelerometer measurements
            for a_index in range(3):
                new_line.append(acel_vals[a_index])

            # Finally add packet ID
            new_line.append(entry[6])

            # Write the new input line to the csv file
            writer.writerow(new_line)




def flight_logger(event, time):
    global flight_log

    new_log = (event, time)
    flight_log.append(new_log)


def error_logger(error_code, time):
    global error_log

    new_error = (error_code, time)
    error_log.append(new_error)

def duration():
    """ Returns current change in time"""
    return format(time.time() - init_time, '.2f')

def flight_time(launch_time):
    return format(time.time() - launch_time, '.2f')

def estimate_velocity():
    global flight_data
    flight_data["velocity"] = 0
    last_r = 0
    """ Finds a poor estimate for velocity in increments of 0.5 seconds"""
    while flight_data["avionics_loop"]:
            init_alt = bmp_sensor.read_altitude()
            sleep(0.5)
            delta_y = ((bmp_sensor.read_altitude() - init_alt) / 0.5)
            if abs(delta_y - last_r) < 102:
                flight_data["velocity"] = delta_y
                last_r = delta_y
            sleep(0.08)

def run_MPU():
    """ Logs acceleration and gyroscope data """

    MPU_Init()    # Setup MPU6050
    global flight_data
    flight_data["accel"] = {
        "Ax" : 0,
        "Ay" : 0,
        "Az" : 0
    }

    flight_data["gyro"] = {
        "Gx" : 0,
        "Gy" : 0,
        "Gz" : 0
    }

    accel_hold, gyro_hold = {}, {}
    while flight_data["avionics_loop"]:
            #Read Accelerometer raw value
            acc_x = read_raw_data(ACCEL_XOUT_H)
            acc_y = read_raw_data(ACCEL_YOUT_H)
            acc_z = read_raw_data(ACCEL_ZOUT_H)

            if acc_x < -10000:
                acc_x /= 2
            acc_x += RAW_AX_OFFSET

            #print("X DATA = " + str(acc_x) + " Z DATA = " + str(acc_z))

            #Read Gyroscope raw value
            gyro_x = read_raw_data(GYRO_XOUT_H)
            gyro_y = read_raw_data(GYRO_YOUT_H)
            gyro_z = read_raw_data(GYRO_ZOUT_H)

            #Full scale range +/- 250 degree/C as per sensitivity scale factor
            flight_data["accel"]["Ax"] = acc_x/16384.0
            flight_data["accel"]["Ay"] = acc_y/16384.0
            flight_data["accel"]["Az"] = acc_z/16384.0

            flight_data["gyro"]["Gx"] = gyro_x/131.0
            flight_data["gyro"]["Gy"] = gyro_y/131.0
            flight_data["gyro"]["Gz"] = gyro_z/131.0







            sleep(0.1)
def show_data():
    global flight_data
    print(flight_data["gyro"])


def altitude():
    global flight_data
    """ Logs current alt to flight_data"""
    flight_data["altitude"] = get_alt()

def flight_status():
    global flight_data
    while flight_data["avionics_loop"]:
        status = ""
        start_alt = get_alt()
        sleep(5)
        if get_alt() > start_alt:
            status = 0
        elif get_alt() < start_alt:
            status = 1
        elif abs(get_alt() - start_alt) < 4:
            status = 2

        flight_data["status"] = status



# Multi-threading Functions
def vel_start():
    global flight_data

    velocity_thread = threading.Thread(target=estimate_velocity)
    velocity_thread.start()

def status_start():
    status_thread = threading.Thread(target=flight_status)
    status_thread.start()

def mpu_start():
    mpu_thread = threading.Thread(target=run_MPU)
    mpu_thread.start()



def alt_start():
    altitude_thread = threading.Thread(target=altitude)
    altitude_thread.start()


# Flight functions

def auto_sequence():
    v, a, m, p = "00000", "0000", "0", "20000"
    command = "v"+v+"_a"+a+"_m"+m+"_p"+p+"\n"
    vega_radio.write(command.encode())
    armed()

def pre_flight():
    return True

def go_launch():
    pf_checks = pre_flight()
    if pf_checks:
        return True
    else:
        return pf_checks


def start_recording(filename=VIDEO_FILENAME, savelocation=VIDEO_SAVELOCATION):
    # Initiate onboard recording
    try:
        file_name = filename + ".h264"
        file_out = save_location + file_name
        onboard_camera.start_recording(file_out)
        flight_logger("started video recording as |" +filename+"| ", duration())

    except:
        flight_logger("unable to start recording, check camera connection", duration())

def stop_recording(filename=VIDEO_FILENAME, savelocation=VIDEO_SAVELOCATION):
    # End onboard recording
    try:
        onboard_camera.stop_recording()
        flight_logger("stopped video recording as |" +filename+"| ", duration())
        flight_logger("video saved to: "+savelocation, duration())

    except:
        flight_logger("unable to stop recording, unknown error", duration())


def armed():
    global configuration
    global flight_log
    global error_log
    # Confirm received:
    v, a, m, p = "00000", "0000", "0", "20000"
    command = "v"+v+"_a"+a+"_m"+m+"_p"+p+"\n"
    vega_radio.write(command.encode())


    flight_logger("armed() initated", duration())
    # Update parkes

    flight_logger("armed_alt: " + str(get_alt()), duration())


    attempts = []
    for attempt in range(3):
        attempts.append(bmp_sensor.read_altitude())
    calibrated_alt = sum(attempts) // 3
    calibrated_acc = 0
    flight_logger("calibrated_alt: " + str(calibrated_alt), duration())
    flight_logger("entering arm loop", duration())


    flight_logger("go/no-go poll running...", duration())
    launch_poll = go_launch()

    if launch_poll == True:
        # send vega is ready
        v, a, m, p = "00000", "0000", "1", "20000"
        command = "v"+v+"_a"+a+"_m"+m+"_p"+p+"\n"
        vega_radio.write(command.encode())
        flight_logger("poll result: GO", duration())
    else:
        # send vega not ready
        v, a, m, p = "00000", "0000", "1", "21111"
        command = "v"+v+"_a"+a+"_m"+m+"_p"+p+"\n"
        vega_radio.write(command.encode())
        flight_logger("poll result: NO GO", duration())
        flight_logger("go_launch() returned: "+ launch_poll, duration())
        error_logger("Exxx")


    flight_log_unload(flight_log, False)
    flight_log = []
    sleep(1)

    if RUN_CAMERA:
        start_recording()

    flight_data["avionics_loop"] = True    # Allows avionics capture

    vel_start()
    status_start()
    mpu_start()
    flight_logger("all multithreads succesful", duration())
    flight_data["flight_record"] = []
    flight_data["flight_record"] = flight(calibrated_alt, calibrated_acc)

    data_unload(flight_data["flight_record"])
    if RUN_CAMERA:
        stop_recording()

    flight_log_unload(flight_log, True)
    error_unload(error_log)




# Data structure = [timestamp, altitude, velocity, data id]
def flight(calib_alt, calib_acc):
    global configuration
    flight_logger("flight() initated", duration())
    # This function is the main flight loop. Let's keep things light boys
    global flight_data
    flight_data["state"] = "flight"
    flight_data["status"] = 2
    data_store = []
    data_id = 0
    recent_command = "v10000_a1000_m8_p1"
    burn_time = configuration["rocket_data"][1]
    deploy_time = burn_time + configuration["rocket_data"][2]
    last_a = bmp_sensor.read_altitude() - calib_alt
    # Timekeeping
    flight_logger("switching to flight time", duration())
    launch_time = time.time()
    flight_logger("flight() loop entered", flight_time(launch_time))

    # THIS IS WHERE THE LAUNCH COMMAND GOES
    v, a, m, p = "00000", "0000", "2", "20000"
    command = "v"+v+"_a"+a+"_m"+m+"_p"+p+"\n"
    vega_radio.write(command.encode())

    # Flight Loop

    test_time = time.time()
    count = 0
    while 1:
        count += 1
        #data_store.append((flight_data["current_time"], data_id))
        current_mode = "m2"
        v, a, m, p = flight_data["velocity"], (bmp_sensor.read_altitude() - calib_alt), current_mode, data_id
        g, c = flight_data["gyro"], flight_data["accel"]
        new_data = [flight_time(launch_time), a, v, m, g, c, p]
        data_store.append(copy.deepcopy(new_data))



        if abs(a - last_a) < 100 and a > 0:
            command = str("v"+str(round(v, 4)).zfill(5)+"_a"+str(round(a, 4)).zfill(4)+"_"+str(m)+"_p"+str(p).zfill(5)+"\n")
            sleep(0.1)
            vega_radio.write(command.encode())
            if command:
                print("this one")
                print(command)
            recent_command = command
        else:
            if command:
                vega_radio.write(recent_command.encode())
                error_logger("E010", flight_time(launch_time))

        data_id += 1
        if float(flight_time(launch_time)) > burn_time + 1:
            current_mode = "m3"

        if flight_data["status"] == 1:
            current_mode = "m4"

        if float(flight_time(launch_time)) > deploy_time + 1:
            current_mode = "m5"

        if abs(get_alt() - calib_alt) < 5:
            if flight_data["status"] == 2:
                current_mode = "m6"

        delay_time = time.time() - test_time

        if delay_time > 30:
            print("done")
            flight_data["avionics_loop"] = False

            return data_store
            break

        sleep(0.1)


def bmp_debug():
    # --- TO BE REMOVED ---
    # This function has been deprecated and is ready for removal.
    # Do not base anything important on this function.
    global data_store
    global flight_data
    while True:
        command = str(flight_data["velocity"])+str(bmp_sensor.read_altitude())+"m2_p00000"
        print(command)
        sleep(0.7)

def demo_loop():
    # This entire function is some demo bullshit and will be removed when the connection issue
    # has been solved. Ignore it. Seriously.
    global data_store
    data_id=demo_vel=demo_alt=current_modetype=0

    while True:
        #data_store.append((flight_data["current_time"], data_id))
        v, a, m, p = demo_vel, demo_alt, "m"+str(current_modetype), data_id
        command = str("v"+str(round(v, 4)).zfill(5)+"_a"+str(round(a, 4)).zfill(4)+"_"+str(m)+"_p"+str(p).zfill(5)+"\n")
        sleep(0.1)
        vega_radio.write(command.encode())
        print(command)

        if demo_vel == 9999:
            demo_vel = 0
        else:
            demo_vel += 5

        if demo_alt == 999:
            demo_alt = 0
        else:
            demo_alt += 1

        if demo_alt % 10 == 0:
            if current_modetype != 7:
                current_modetype += 1
            else:
                current_modetype = 0

        sleep(0.1)




def open_port():
    global vega_radio
    # Opens the default port for Vega transceiver
    vega_radio = serial.Serial(
        port = "/dev/serial0",
        baudrate = 9600,
        parity = serial.PARITY_NONE,
        stopbits = serial.STOPBITS_ONE,
        bytesize = serial.EIGHTBITS,

        # You might need a timeout here if it doesn't work, try a timeout of 1 sec
        )
def send(vamp):
    # Sends command over radio
    try:
        v, a, m, p = vamp
    except:
        error("E310")
    command = "v"+str(v)+"_a"+str(a)+"_m"+str(m)+"_p"+str(p)+"\n"
    vega_radio.write(command.encode())

def receive():
    # Listens for a vamp from Vega. Simples
    data = vega_radio.read_until()
    to_return = data
    to_return = to_return.decode()
    return to_return


def vamp_destruct(vamp):
    vamp_decom = []
    for element in vamp.split("_"):
        vamp_decom.append(element[1:])

    try:
        v, a, m, p = vamp_decom
    except:
        error("E120")
    vamp = (int(v), int(a), int(m), int(p))

    return vamp

def set_beep(value):
    global configuration
    configuration["beep_vol"] = int(value)

def set_debug(value):
    global configuration
    try:
        if value == "True":
            configuration["debug_mode"] = True
        else:
            configuration["debug_mode"] = False
        return True
    except:
        return False

def config_update(data):
    target, value = data[0], data[1:]

    function_definitions = {
        "A" : set_beep,
        "B" : set_debug
    }
    try:
        return function_definitions[target](value)

    except:
        return False


def receive_config():
    new_command = vega_radio.read_until().decode().split("|")
    flight_logger("UPDATING CONFIG", duration())
    con_count, con_list = 0, ""

    for update in new_command:
        result = config_update(update)

        if result:
            con_count += 1
            con_list += "|" + update


    return_update = str(con_count) + "." + con_list
    flight_logger(return_update, duration())
    vega_radio.write(return_update.encode())
    flight_logger("CONFIG UPDATE COMPLETE", duration())



def heartbeat():
    global vega_radio

    # Receive Handshake

    # Confirm handshake
    to_send = "v10000_a1000_m8_p00000\n"
    vega_radio.write(to_send.encode())

    # Start heartbeat
    # Heartbeat Loop
    beat = 1
    vega_radio.timeout = 0.6
    heartbeat_loop = True
    while heartbeat_loop:
        to_send = "v10000_a1000_m8_p"
        to_send = to_send + str(beat).zfill(5) + "\n"

        vega_radio.write(to_send.encode())
        sleep(0.6)
        print("Heartbeat Away... (" +str(beat)+") ("+to_send+")")
        beat += 1
        check_kill = ""
        check_kill = vega_radio.read_until().decode()
        if "v10000_a1000_m8_p" in check_kill:
            flight_logger("heartbeat() kill acknowledged", duration())
            heartbeat_loop = False
        if "config_update" in check_kill:
            flight_logger("config_update acknowledged", duration())
            receive_config()

    vega_radio.timeout = None


def arm():
    flight_logger("DEBUG: disabled rec_command", duration())
    armed()

def heartbeat_init():
    flight_logger("heartbeat command received", duration())
    vega_radio.write("v10000_a1000_m8_p00000\n".encode())
    heartbeat()

def force_launch():
    flight_logger("FORCING LAUNCH", duration())
    flight_logger("LAUNCH DETCTED", duration())
    vel_start()
    flight(get_alt(), 0)

def compile_logs():
    flight_logger("COMPILING LOGS...", duration())
    flight_log_unload(flight_log)
    error_unload(error_log)
    sleep(1)





# STARTUP
init_time = time.time()
flight_logger("vega flight system - startup", duration())
flight_logger("initialising vfs - verison: " + str(vega_version), duration())
open_port()
time.sleep(1)
flight_logger("port open", duration())

command_dict = {
    0 : arm,
    2 : force_launch,
    3 : demo_loop,
    4 : compile_logs,
    7 : receive_config,
    8 : heartbeat_init
}

while receiving_command:
    print("RECEIVING COMMAND...")
    flight_logger("RECEIVING COMMAND...", duration())

    new_command = vamp_destruct(receive())
    flight_logger("COMMAND: " + str(new_command), duration())

    target_program = new_command[2]
    target_comp = int(str(new_command[3])[0])
    if __name__ == "__main__":
        try:
            # Check vega was the intended target
            if int(target_comp) == COMP_ID:
                command_dict[target_program]()
            else:
                flight_logger("command detected - not for Vega", duration())
                print("Comp id = " + str(COMP_ID) +", Target id = " + str(target_comp))

        except KeyboardInterrupt:
            flight_logger("KeyboardInterrupt detected", duration())
            flight_logger("port closed", duration())
            compile_logs()


      # do noth
