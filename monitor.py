#!/usr/bin/env python

import sys, getopt, commands, time, thread, json
import serial
import requests

url = 'http://api.heclouds.com/devices/3289515/datapoints?type=3'
headers = {'api-key': 'HP57BMt3dMQg4VbHBL7izleBeU8='}

ifname = None
at_serial_port = None
gps_serial_port = None


def at_command(c):
    if at_serial_port is None:
        return
    at_serial_port.write('%s\r' % c)
    data = at_serial_port.read(1)
    if data:
        n = at_serial_port.inWaiting()
        if n:
            data = data + at_serial_port.read(n)
    return data


def at_cops():
    ret = at_command('AT+COPS?')
    if ret:
        s = ret.find('+COPS: ')
        e = ret.find('\r', s)
        if s > 0:
            cops = ret[s + 7:e].split(',', 4)
            oper = cops[2].replace('"', '')
            act = cops[3]
            if act == '0':
                return '%s GSM' % oper
            elif act == '2':
                return '%s TD-SCDMA' % oper
            elif act == '7':
                return '%s LTE' % oper
    return ''


def at_csq():
    ret = at_command('AT+CSQ')
    if ret:
        s = ret.find('+CSQ: ')
        e = ret.find(',', s)
        if s > 0:
            rssi = int(ret[s + 6:e])
            if rssi > 0 and rssi < 100:
                return rssi * 2 - 113
            elif rssi >= 100 and rssi <= 199:
                return rssi - 216
    return 0


def network_report_thread():
    while True:
        # read interface rx or tx value
        (status, before_rx_total) = commands.getstatusoutput(
            'ifconfig %s | sed -n 8p | awk -F":" \'{print $2}\' | awk \'{print $1}\'' % ifname)
        if status:
            return

        (status, before_tx_total) = commands.getstatusoutput(
            'ifconfig %s | sed -n 8p | awk -F":" \'{print $3}\' | awk \'{print $1}\'' % ifname)
        if status:
            return

        time.sleep(1)

        (status, after_rx_total) = commands.getstatusoutput(
            'ifconfig %s | sed -n 8p | awk -F":" \'{print $2}\' | awk \'{print $1}\'' % ifname)
        if status:
            return 0

        (status, after_tx_total) = commands.getstatusoutput(
            'ifconfig %s | sed -n 8p | awk -F":" \'{print $3}\' | awk \'{print $1}\'' % ifname)
        if status:
            return 0

        rx_diff = long(after_rx_total) - long(before_rx_total)
        tx_diff = long(after_tx_total) - long(before_tx_total)

        rx, rx_rate, tx, tx_rate = '%.2f' % (long(after_rx_total) / float(1024 * 1024)), rx_diff / 1024, '%.2f' % (
        long(after_tx_total) / float(1024 * 1024)), tx_diff / 1024
        # print rx, rx_rate, tx, tx_rate

        # post data to heclouds
        payload = json.dumps(
            {"cops": at_cops(), "csq": at_csq(), "rx": rx, "rx_rate": rx_rate, "tx": tx, "tx_rate": tx_rate})
        print time.ctime(), 'request:\t', payload
        resp = requests.post(url, headers=headers, data=payload)
        print time.ctime(), 'response:\t', resp.text

        time.sleep(4)


def gps_report_thread():
    while True:
        data = gps_serial_port.read(1)
        if data:
            n = gps_serial_port.inWaiting()
            if n:
                data = data + gps_serial_port.read(n)
                # if data.startswith('$GPGSV'):
                s = data.find('$GPGGA')
                e = data.find('\r', s)
                if s > 0:
                    #print data[s:e]
                    nmea = data[s:e].split(',', 14)
                    if nmea[1]:
                        # print '%s%s'%(nmea[2],nmea[3]),'%s%s'%(nmea[4],nmea[5]),'%s%s'%(nmea[9],nmea[10]),nmea[7]
                        payload = json.dumps({"lat": '%s%s' % (nmea[2], nmea[3]), "lon": '%s%s' % (nmea[4], nmea[5]),
                                              "alt": '%s%s' % (nmea[9], nmea[10]), "sate": nmea[7]})
                        print time.ctime(), 'request:\t', payload
                        resp = requests.post(url, headers=headers, data=payload)
                        print time.ctime(), 'response:\t', resp.text
        time.sleep(5)


def usage():
    print '''
Usage:monitor.py [-i <interface_name> [-a <at_serial_port> [-p <gps_serial_port>]]]
                 [-i <interface_name> [-m <modem_name>]]
                 [-h or --help]
Options:
    -i: interface_name eg. eth1 or eth0.1
    -a: at_serial_port eg. /dev/ttyUSB0
    -g: gps_serial_port eg. /dev/ttyUSB1
    -m: modem_name eg. e3276 or me3760 or u8300w
    -h or --help: print usage
Example:
    ./monitor.py -i enp0s25 -a /dev/ttyUSB2 -g /dev/ttyUSB3
    ./monitor.py -i enp0s25 -m me3760
'''

# Longsung U8300W  port: AT ttyUSB2   GPS-NMEA ttyUSB3
# ZTE ME3760       port: AT ttyUSB1
# Huawei E3276     port: AT ttyUSB1
if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h:i:a:g:m:", ["help"])
        for op, value in opts:
            if op == "-i":
                ifname = value
            elif op == "-a":
                at_serial_port = serial.Serial(value,115200, timeout=1)
            elif op == "-g":
                gps_serial_port = serial.Serial(value,115200, timeout=1)
            elif op == "-m":
                if value == 'e3276':
                    #print "Huawei E3276"
                    at_serial_port = serial.Serial('/dev/ttyUSB1', 115200, timeout=1)
                elif value == 'me3760':
                    #print "ZTE ME3760"
                    at_serial_port = serial.Serial('/dev/ttyUSB1', 115200, timeout=1)
                elif value == 'u8300w':
                    #print "LONGSUNG U8300W"
                    at_serial_port = serial.Serial('/dev/ttyUSB2', 115200, timeout=1)
                    gps_serial_port = serial.Serial('/dev/ttyUSB3', 115200, timeout=1)
            elif op in ("-h", "--help"):
                usage()
                sys.exit()

        if ifname is None:
            sys.exit()

        if not at_serial_port is None:
            #close at echo
            at_command('ATE0')
            if not gps_serial_port is None:
                #Longsung U8300W
                at_command('AT+GPSMODE=1')
                at_command('AT+GPSSTART')
                time.sleep(0.5)
                thread.start_new_thread(gps_report_thread,())

        #thread.start_new_thread(network_report_thread,(ifname,))
        thread.start_new_thread(network_report_thread,())
        while True:
            pass
    except getopt.GetoptError, e:
        print 'Exception:', e
    except KeyboardInterrupt:
        sys.exit()
    finally:
        if not at_serial_port is None:
            at_serial_port.close()
        if not gps_serial_port is None:
            gps_serial_port.close()