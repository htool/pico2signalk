#!/usr/bin/python

import time
import socket
import sys 
import select
import requests
import json

responses = [''] * 200
sensors = ['']

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def empty_socket(sock):
    """remove the data present on the socket"""
    input = [sock]
    while 1:
        inputready, o, e = select.select(input,[],[], 0.0)
        if len(inputready)==0: break
        for s in inputready: s.recv(1)

def striplist(l):
    return([x.strip() for x in l])

def HexToByte( hexStr ):
    """
    Convert a string hex byte values into a byte string. The Hex Byte values may
    or may not be space separated.
    """
    bytes = []
    hexStr = ''.join( hexStr.split(" ") )
    for i in range(0, len(hexStr), 2):
        bytes.append( chr( int (hexStr[i:i+2], 16 ) ) )
    return ''.join( bytes )

def ByteToHex( byteStr ):
    """
    Convert a byte string to it's hex string representation e.g. for output.
    """
    return ''.join( [ "%02X " % ord( x ) for x in byteStr ] ).strip()

def HexToInt(hex,lastBytes):
    return int(hex.replace(' ','')[-lastBytes:], 16)

def IntToDecimal(integer):
    return integer / float(10)

def BinToHex(message):
  response = ''
  for x in message:
    hex = x.encode('hex')
    response = response + hex + ' '
  return response

def parse(message):
  values = message.split(' ff')
  values = striplist(values)
  return values

def send_receive(message):
  bytes = message.count(' ') + 1
  # print ("Sending : " + message + " (" + str(bytes) + " bytes)")
  message = HexToByte(message)
  s.sendall(message)
  response = ''
  hex = ''
  for x in s.recv(1024):
    priv_hex = hex
    hex = x.encode('hex')
    response = response + hex + ' '
  return response

def open_tcp(pico_ip):
  try:
    # Create a TCP stream socket with address family of IPv4 (INET)
    serverport = 5001
    # Connect to the server at given IP and port
    s.connect((pico_ip, serverport))
    return
  except:
    print "Connection to " + pico_ip + ":5001 failed. Retrying in 1 sec."
    time.sleep(1)
    # try again
    return open_tcp(pico_ip)
  
def get_pico_config(pico_ip):
  open_tcp(pico_ip)

  message = "00 00 00 00 00 ff 41 04 8c 55 4b 00 16 ff 00 01 00 00 00 00 ff 01 03 00 00 00 00 ff 00 00 00 00 ff e8 19"
  response = send_receive(message)
  # print str(parse(response))
  # CRC checksums (due to lack of knowing how to calculate these)
  CRCs = ('e8 19','3c 33','51 c4','85 ee','8a 2a','5e 00','33 f7','e7 dd','2c 7f','f8 55','95 a2','41 88','4e 4c','9a 66','f7 91','23 bb','71 5c','a5 76','c8 81','1c ab','13 6f','c7 45','aa b2','7e 98','b5 3a','61 10')
  response_list = []
  fluid = ['fresh water','diesel']
  fluid_type = ['freshWater','fuel']
  pos = 0
  for crc in CRCs:
    sensor_name = ''
    sensor_type = ''
    sensor_capacity = 0
    sensor_fluid = ''
    message = ('00 00 00 00 00 ff 41 04 8c 55 4b 00 16 ff 00 01 00 00 00 ' + "%02x" % pos + ' ff 01 03 00 00 00 00 ff 00 00 00 00 ff ' + crc)
    response = send_receive(message)
    if response != '':
      response_list = parse(response)
    if len(response_list) > 6:
      responses[pos] = response_list[7].replace(' ','').decode('hex')
      sensor_name = response_list[7].replace(' ','').decode('hex')
    if pos == 5:
      sensor_name = 'Barometer'
      sensor_type = 'pressure'
      # print "Sensor name: " + sensor_name + "  type: " + str(sensor_type)
    if pos == 8:
      sensor_name = 'Service'
      sensor_type = 'Battery'
      # print "Sensor name: " + sensor_name + "  type: " + str(sensor_type)
    if pos >= 19:
      try:
        capacityHex = response_list[13].replace(' ','')
        sensor_capacity = int(capacityHex[4:8],16) / 10
        fluidHex = response_list[11].replace(' ','')
        sensor_fluid = fluid[int(fluidHex[4:8],16) - 1]
        sensor_type = fluid_type[int(fluidHex[4:8],16) - 1]
        # print "Sensor name: " + sensor_name + "  type: " + str(sensor_type) + "  fluid: " + sensor_fluid + "  capacity: " + str(sensor_capacity)
        updates.append({"path": "tanks." + sensor_type + ".1.name", "value": sensor_name})
        updates.append({"path": "tanks." + sensor_type + ".1.type", "value": sensor_fluid})
        updates.append({"path": "tanks." + sensor_type + ".1.capacity", "value": sensor_capacity})
      except:
        try:
          capacityHex = response_list[11].replace(' ','')
          sensor_capacity = int(capacityHex[4:8],16) / 100
          sensor_type = 'battery'
          # print "Sensor name: " + sensor_name + "  type: " + str(sensor_type) + "  capacity: " + str(sensor_capacity)
        except:
          sensor_type = 'temperature'
          # print "Sensor name: " + sensor_name + "  type: " + str(sensor_type)
      # print (responses[pos] + "  " + str(response_list))
    pos += 1

  # Close tcp connection
  s.close()

get_pico_config('192.168.4.225')

# exit()

# print "Start UDP listener"

# Setup UDP broadcasting listener
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
client.bind(("", 43210))

responseB = [''] * 50
responseC = []

while True:
    updates = []
    message, addr = client.recvfrom(1024)
    if responses[0] == '':
      get_pico_config(addr[0])
    response = BinToHex(message)
    if response[18] == 'b':
      if len(response) == 0:
        continue
      else:
        pos = 0
    # Strip header to avoid confusion
    response = response[42:]
    # for part in parse(response):
    while pos < 43:
      part = response[0:18]
      response = response[21:]
      pos = int(part[0:2], 16)
      # print "pos: " + str(pos) + "  part: " + part # + "   response: " + response
      part = part[6:].replace(' ','')
      if pos < 43:
        # if responseB[pos] != part:
        # print part + " " + str(pos) + " was: " + str(responseB[pos])
        if pos == 5:
          voltage = int(part, 16) / float(1000)
        #  print responses[pos-1] + " " + voltage + ' volt'
        # if pos == 14:
        #  print responses[pos-1] + " " + str(int(part,16)) + ' Ohm'
        if pos == 3:
          pressure = int(part[4:8],16) + 65536
          #print responses[pos-1] + " " + pressure + ' mBar'
          updates.append({"path": "environment.outside.pressure", "value": pressure})
        if pos == 19:
          temp = ("%.2f" % round(int(part,16) / float(10) + 273.15, 2))
          updates.append({"path": "environment.inside.temperature", "value": temp})
          # print responses[pos-1] + " " + str(temp) + ' K'
        if pos == 20: # Water tank voor
          percent = int(part[1:4],16) / float(1000)
          liter = int(part[4:8],16) / float(10000)
          updates.append({"path": "tanks.freshWater.1.currentLevel", "value": percent})
          updates.append({"path": "tanks.freshWater.1.currentVolume", "value": liter})
          updates.append({"path": "tanks.freshWater.1.name", "value": "Voor"})
          updates.append({"path": "tanks.freshWater.1.type", "value": "fresh water"})
          updates.append({"path": "tanks.freshWater.1.capacity", "value": "200"})
        if pos == 23: # Service battery
          voltage = int(part, 16) / float(1000)
          updates.append({"path": "electrical.batteries.1.name", "value": 'Service'})
          updates.append({"path": "electrical.batteries.1.capacity", "value": '240'})
          updates.append({"path": "electrical.batteries.1.voltage", "value": voltage})
          updates.append({"path": "electrical.batteries.1.temperature", "value": temp})
        if pos == 26: # Water tank achter
          percent = int(part[1:4],16) / float(1000)
          liter = int(part[4:8],16) / float(10000)
          updates.append({"path": "tanks.freshWater.2.currentLevel", "value": percent})
          updates.append({"path": "tanks.freshWater.2.currentVolume", "value": liter})
          updates.append({"path": "tanks.freshWater.2.name", "value": "Achter"})
          updates.append({"path": "tanks.freshWater.2.type", "value": "fresh water"})
          updates.append({"path": "tanks.freshWater.2.capacity", "value": "160"})
        if pos == 27: # Diesel tank
          percent = int(part[1:4],16) / float(1000)
          liter = int(part[4:8],16) / float(10000)
          updates.append({"path": "tanks.fuel.1.currentLevel", "value": percent})
          updates.append({"path": "tanks.fuel.1.currentVolume", "value": liter})
          updates.append({"path": "tanks.fuel.1.name", "value": "Diesel"})
          updates.append({"path": "tanks.fuel.1.type", "value": "diesel"})
          updates.append({"path": "tanks.fuel.1.capacity", "value": "160"})
        if pos == 30: # Start battery
          voltage = int(part, 16) / float(1000)
          updates.append({"path": "electrical.batteries.2.name", "value": 'Start'})
          updates.append({"path": "electrical.batteries.2.capacity", "value": '105'})
          updates.append({"path": "electrical.batteries.2.voltage", "value": voltage})
          updates.append({"path": "electrical.batteries.2.temperature", "value": temp})
        if pos == 35: # Ankerlier battery
          voltage = int(part, 16) / float(1000)
          updates.append({"path": "electrical.batteries.3.name", "value": 'Ankerlier'})
          updates.append({"path": "electrical.batteries.3.capacity", "value": '105'})
          updates.append({"path": "electrical.batteries.3.voltage", "value": voltage})
          updates.append({"path": "electrical.batteries.3.temperature", "value": temp})
        if pos == 40: # Boegschroef battery
          voltage = int(part, 16) / float(1000)
          updates.append({"path": "electrical.batteries.4.name", "value": 'Boegschroef'})
          updates.append({"path": "electrical.batteries.4.capacity", "value": '50'})
          updates.append({"path": "electrical.batteries.4.voltage", "value": voltage})
          updates.append({"path": "electrical.batteries.4.temperature", "value": temp})

        responseB[pos] = part
      pos += 1

    delta = {
        "updates": [
              {
                "source": {
                    "label": "Simarine Pico"
                },
                "values": updates
            }
        ]
    }
    print json.dumps(delta)
    sys.stdout.flush()
    time.sleep (1)
    empty_socket(client)
