#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016 Jeff Stevens
# SR700-Artisan-PDServer, released under GPLv3

#Extended by Luca Pinello @lucapinello

import signal
import sys
import time
import sys
from freshroastsr700_phidget import SR700Phidget
import logging
import Pyro4
import Pyro4.naming
import os
import subprocess as sb
import argparse


import signal
import time
import sys

def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)

    try:
        if raw_input("\nReally quit? (y/n)> ").lower().startswith('y'):
            sys.exit(1)

    except KeyboardInterrupt:
        print("Ok ok, quitting")
        sys.exit(1)

    # restore the exit gracefully handler here
    signal.signal(signal.SIGINT, exit_gracefully)


@Pyro4.expose
class Roaster(object):
    def __init__(self,use_phidget_temp=True,
                phidget_use_hub=False,
                phidget_hub_port=0,
                phidget_hub_channel=4,
                kp=0.4, ki=0.0075, kd=0.9):

        """Creates a freshroastsr700 object passing in methods included in this
        class."""

        self.use_phidget_temp=use_phidget_temp
        self.roaster = SR700Phidget(
	        use_phidget_temp=use_phidget_temp,
            phidget_use_hub=phidget_use_hub,
            phidget_hub_port=phidget_hub_port,
            phidget_hub_channel=phidget_hub_channel,
            update_data_func=self.update_data,
            state_transition_func=self.next_state,
            thermostat=True,
            kp=kp,
            ki=ki,
            kd=kd)

    def update_data(self):
        """This is a method that will be called every time a packet is opened
        from the roaster."""
        cur_state = self.roaster.get_roaster_state()

        if self.roaster.log_info:

            if self.use_phidget_temp:
                logging.info("[State:%s] Temp SR700:%d Temp Phidget %d Target temp: %d Fan Speed: %d Time left: %d"  % \
                ( str(cur_state),
                self.roaster.current_temp,
                self.roaster.current_temp_phidget,
                self.roaster.target_temp,
                self.roaster.fan_speed,
                self.roaster.time_remaining))
            else:
                logging.info("[State:%s] Temp SR700:%d Target temp: %d Fan Speed: %d Time left: %d"  % \
                ( str(cur_state),
                self.roaster.current_temp,
                self.roaster.target_temp,
                self.roaster.fan_speed,
                self.roaster.time_remaining))

    def next_state(self):
        """This is a method that will be called when the time remaining ends.
        The current state can be: roasting, cooling, idle, sleeping, connecting,
        or unkown."""
        if(self.roaster.get_roaster_state() == 'roasting'):
            self.roaster.time_remaining = 20
            self.roaster.cool()
        elif(self.roaster.get_roaster_state() == 'cooling'):
            self.roaster.idle()

    def run_roast(self):
        if(self.roaster.get_roaster_state() == 'idle'):
            self.roaster.roast()

    def run_cooling(self):
        self.roaster.cool()

    def stop(self):
            self.roaster.idle()

    def set_fan_speed(self, speed):
        new_speed = int(speed)
        self.roaster.fan_speed = new_speed

    def set_temperature(self, temperature):
        new_temperature = int(temperature)
        if new_temperature < 120:
            self.roaster.cool()
        else:
            self.roaster.target_temp = new_temperature

    def set_time(self, time):
        new_time = int(time)
        self.roaster.time_remaining = new_time

    def output_current_state(self):
        cur_state = self.roaster.get_roaster_state()
        cur_temp = str(self.roaster.current_temp)
        ret_state = cur_temp + cur_state
        return ret_state

    def output_sr700_and_phidget_temp(self):
        cur_state = self.roaster.get_roaster_state()
        cur_temp = str(self.roaster.current_temp)
        ret_state = cur_temp + cur_state
        return self.roaster.current_temp,self.roaster.current_temp_phidget

def main():

    try:
        print(
'''
      _____ _____  ______ ___   ___
     / ____|  __ \|____  / _ \ / _ \\
    | (___ | |__) |   / / | | | | | |
     \___ \|  _  /   / /| | | | | | |
     ____) | | \ \  / / | |_| | |_| |
    |_____/|_|  \_\/_/   \___/ \___/
     /\        | | (_)
    /  \   _ __| |_ _ ___  __ _ _ __
   / /\ \ | '__| __| / __|/ _` | '_ \\
  / ____ \| |  | |_| \__ \ (_| | | | |
 /_/ ___\_\_|   \__|_|___/\__,_|_| |_|
    / ____|
   | (___   ___ _ ____   _____ _ __
    \___ \ / _ \ '__\ \ / / _ \ '__|
    ____) |  __/ |   \ V /  __/ |
   |_____/ \___|_|    \_/ \___|_|
   ''')

        print('SR700 Artisan Server - Luca Pinello 2019 (@lucapinello)\n\n')
        print('Send bugs, suggestions or *green coffee* to lucapinello AT gmail DOT com\n')

        signal.signal(signal.SIGINT, signal_handler)

        parser = argparse.ArgumentParser(description='Parameters',formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--enable_extension', type=str, help='Running mode: phidget_simple,\
        phidget_hub if not specified no external sensor will be used,',
        default='simple',choices=['simple','phidget_simple','phidget_hub'] )
        parser.add_argument('--phidget_hub_port',  type=int,  default=0)
        parser.add_argument('--phidget_hub_channel',  type=int,  default=4)
        parser.add_argument('--kp',  type=float, default=None)
        parser.add_argument('--ki',  type=float, default=None)
        parser.add_argument('--kd',  type=float, default=None)


        args = parser.parse_args()


        assign_pid_param=lambda v_args,v_default: v_args if v_args else v_default

        if args.enable_extension=='phidget_simple' or args.enable_extension=='phidget_hub':

            use_phidget_temp=True

            kp=assign_pid_param(args.kp,0.4)
            ki=assign_pid_param(args.ki,0.0075)
            kd=assign_pid_param(args.kd,0.9)

        else:
            use_phidget_temp=False

            kp=assign_pid_param(args.kp,0.06)
            ki=assign_pid_param(args.ki,0.0075)
            kd=assign_pid_param(args.kd,0.01)


        if args.enable_extension=='phidget_hub':
            phidget_use_hub=True
        else:
            phidget_use_hub=False


        nameserver_process=None
        r=None

        # Set logging
        logging.getLogger("Pyro4.core").setLevel(logging.CRITICAL)

        logging.getLogger("Pyro4.name").setLevel(logging.ERROR)

        logging.basicConfig(level=logging.INFO,
                     #format='%(levelname)-5s @ %(asctime)s:-[[\t%(message)s]]-',
                     format='-[[\t%(message)s\t]]-',
                     datefmt='%a, %d %b %Y %H:%M:%S',
                     stream=sys.stderr,
                     filemode="w"
                     )
        #logging.basicConfig(filename="RoastControl_debug_log.log",level=logging.DEBUG)


        logging.info('Starting Nameserver...')
        with open(os.devnull, 'w') as fp:
            nameserver_process=sb.Popen(['python', '-m','Pyro4.naming'],stdout=fp)

        ##Pyro4.naming.startNS()
        time.sleep(1)

        logging.info('Starting Server')
        daemon = Pyro4.Daemon()                # make a Pyro daemon
        ns = Pyro4.locateNS()


        logging.info("Initializing connection with the SR700...")
        # Create a roaster object.
        r = Roaster(use_phidget_temp=use_phidget_temp,
        phidget_use_hub=phidget_use_hub,
        phidget_hub_port=args.phidget_hub_port,
        phidget_hub_channel=args.phidget_hub_channel,
        kp=kp,ki=ki,kd=kd)

        r.roaster.log_info=False

        # Conenct to the roaster.
        r.roaster.auto_connect()


        # Wait for the roaster to be connected.
        while(not(r.roaster.connected)):

            if r.roaster.phidget_error:
                raise Exception('Phidget Error!')

            time.sleep(2)

            if not(r.roaster.connected):
                logging.info("Still waiting for connection...")

            time.sleep(2)

            if not(r.roaster.connected):
                logging.info('Please check if the roaster is connected')

        if r.roaster.phidget_error:
            raise Exception('Phidget Error!')

        uri = daemon.register(r)
        ns.register("roaster.sr700", uri)
        logging.info('Server Ready!')
        r.roaster.log_info=True
        daemon.requestLoop()





    except Exception as e:

        logging.error(e)

        if nameserver_process:
            nameserver_process.kill()

        if r:
            r.roaster.terminate()

        print('\nSend bugs, suggestions or *green coffee* to lucapinello AT gmail DOT com\n')

        print('Bye!\n')
        sys.exit(0)


def signal_handler(sig, frame):
    #print('You pressed Ctrl+C!')
    raise Exception

if __name__ == '__main__':
    main()
