#!/usr/bin/python

import os
import time
import socket
import sys
import select
import requests
import json
import brainsmoke
import copy
import dictdiffer


responses = [''] * 200
sensors = ['']



def debug(string):
    if "DEBUG" in os.environ:
      if os.environ['DEBUG'] == 'pico':
        print (string)
        sys.stdout.flush()

def empty_socket(sock):
    """remove the data present on the socket"""
    input = [sock]
    while 1:
        inputready, o, e = select.select(input,[],[], 0.0)
        if len(inputready)==0: break
        for s in inputready: s.recv(1)

def striplist(l):
    return([x.strip() for x in l])

def hexdump(b):
    hex = ' '.join(["%02x" % b ])
    if (len(hex) == 3):
      hex = "0" + hex
    if (len(hex) == 2):
      hex = "00" + hex
    return hex[0:2] + " " + hex[2:4]

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
      hexy = format(x, '02x')
      response = response + hexy + ' '
    return response

def parse(message):
    values = message.split(' ff')
    values = striplist(values)
    return values

def getNextField(response):
  # debug( "field_nr: " + response[0:2])
  field_nr = int(response[0:2], 16)
  # debug( "field_type: " + response[3:6])
  field_type = int(response[3:5] , 16)
  if (field_type == 1):
      # debug( response)
      # debug( "a: " + response[6:11].replace(' ',''))
      # debug( "b: " + response[12:17].replace(' ',''))
      data = response[6:17]
      # debug( "data: " + data)
      response = response[21:]
      # if (data[0:11] == '7f ff ff ff'):
        # return field_nr, '', response
      # else:
      a = int(data[0:5].replace(' ','') , 16)
      b = int(data[6:11].replace(' ','') , 16)
       # field_data = [a, b, data]
      field_data = [a, b]
      return (field_nr, field_data, response)
  if (field_type == 3):
      # debug( response)
      # debug( "a: " + response[21:27].replace(' ',''))
      # debug( "b: " + response[27:32].replace(' ',''))
      data = response[21:32]
      # debug( "data: " + data)
      response = response[36:]
      if (data[0:11] == '7f ff ff ff'):
        return field_nr, '', response
      else:
        a = int(data[0:5].replace(' ','') , 16)
        b = int(data[6:11].replace(' ','') , 16)
        # field_data = [a, b, data]
        field_data = [a, b]
        return field_nr, field_data, response
  if (field_type == 4): # Text string
      # Strip first part
      response = response[21:]
      nextHex = response[0:2]
      word = ''
      while (nextHex != '00'):
        word += nextHex
        response = response[3:]
        nextHex = response[0:2]
      word = HexToByte(word)
      # debug( "Word: " + word)
      response = response[6:] # Strip seperator
      return field_nr, word, response
  debug( "Uknown field type " + str(field_type))

def parseResponse(response):
  dict = {}
  # strip header
  response = response[42:]
  while (len(response) > 6):
    field_nr, field_data, response = getNextField(response)
    # debug( str(field_nr) + " " + field_data)
    # debug( response + " " + str(len(response)))
    dict[field_nr] = field_data
  return dict

def add_crc(message):
  fields=message.split()
  message_int=[int(x,16) for x in fields[1:]]
  crc_int = brainsmoke.calc_rev_crc16(message_int[0:-1])
  return message + " " + hexdump(crc_int)

def send_receive(message):
  bytes = message.count(' ') + 1
  # debug( ("Sending : " + message + " (" + str(bytes) + " bytes)"))
  message = bytearray.fromhex(message)
  s.sendall(message)
  response = ''
  hex = ''
  for x in s.recv(1024):
    hex = format(x, '02x')
    response = response + hex + ' '
  # debug('Response: ' + response)
  return response

def open_tcp(pico_ip):
  try:
    # Create a TCP stream socket with address family of IPv4 (INET)
    serverport = 5001
    # Connect to the server at given IP and port
    s.connect((pico_ip, serverport))
    return
  except:
    debug( "Connection to " + str(pico_ip) + ":5001 failed. Retrying in 1 sec.")
    time.sleep(5)
    # try again
    return open_tcp(pico_ip)

def get_pico_config(pico_ip):
  config = {}
  open_tcp(pico_ip)
  response_list = []
  message = ('00 00 00 00 00 ff 02 04 8c 55 4b 00 03 ff')
  message = add_crc(message)
  response = send_receive(message)
  # debug( "Response: " + response)
  # Response: 00 00 00 00 00 ff 02 04 8c 55 4b 00 11 ff 01 01 00 00 00 1e ff 02 01 00 00 00 30 ff 32 cf
  req_count = int(response.split()[19], 16) + 1
  # debug( "req_count: " + str(req_count))

  for pos in range(req_count):
    message = ('00 00 00 00 00 ff 41 04 8c 55 4b 00 16 ff 00 01 00 00 00 ' + "%02x" % pos + ' ff 01 03 00 00 00 00 ff 00 00 00 00 ff')
    message = add_crc(message)
    response = send_receive(message)
    element = parseResponse(response)
    config[pos] = element

  # Close tcp connection
  s.close()
  return config

def toTemperature (temp):
  # Unsigned to signed
  if temp > 32768:
      temp = temp - 65536
  temp2 = float(("%.2f" % round(temp / float(10) + 273.15, 2)))
  return temp2

def createSensorList (config):
  sensorList = {}
  fluid = ['Unknown', 'freshWater', 'fuel','wasteWater']
  fluid_type = ['Unknown', 'fresh water', 'diesel','blackwater']
  elementPos = 0
  for entry in config.keys():
    # debug( config[entry])
    # Set id
    id = config[entry][0][1]
    # Set type
    type = config[entry][1][1]
    # Default elementsize
    elementSize = 1
    sensorList[id] = {}
    if (type == 0):
      type = 'null'
      elementSize = 0
    if (type == 1):
      type = 'volt'
      sensorList[id].update ({'name': config[entry][3]})
      if (config[entry][3] == 'PICO INTERNAL'):
        elementSize = 6
    if (type == 2):
      type = 'current'
      sensorList[id].update ({'name': config[entry][3]})
      elementSize = 2
    if (type == 3):
      type = 'thermometer'
      sensorList[id].update ({'name': config[entry][3]})
    if (type == 5):
      type = 'barometer'
      sensorList[id].update ({'name': config[entry][3]})
      elementSize = 2
    if (type == 6):
      type = 'ohm'
      sensorList[id].update ({'name': config[entry][3]})
    if (type == 8):
      type = 'tank'
      sensorList[id].update ({'name': config[entry][3]})
      sensorList[id].update ({'capacity': config[entry][7][1]/10})
      sensorList[id].update ({'fluid_type': fluid_type[config[entry][6][1]]})
      sensorList[id].update ({'fluid': fluid[config[entry][6][1]]})
    if (type == 9):
      type = 'battery'
      sensorList[id].update ({'name': config[entry][3]})
      sensorList[id].update ({'capacity.nominal': config[entry][5][1]*36*12}) # In Joule
      elementSize = 5
    if (type == 14):
      type = 'XX'
      elementSize = 1

    sensorList[id].update ({'type': type, 'pos': elementPos})
    elementPos = elementPos + elementSize
  return sensorList

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
debug( "Start UDP listener")
# Setup UDP broadcasting listener
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
client.bind(("", 43210))

# Assign pico address
message, addr = client.recvfrom(2048)
pico_ip = addr[0]
debug("See Pico at " + str(pico_ip))


config = get_pico_config(pico_ip)
debug("CONFIG:")
debug(config)

# sensorList = {}
sensorList = createSensorList(config)
debug("SensorList:")
debug(sensorList)

# exit(0)


responseB = [''] * 50
responseC = []

old_element = {}

def readBaro (sensorId, elementId):
    sensorListTmp[sensorId].update({'pressure': element[elementId][1] + 65536})

def readTemp (sensorId, elementId):
    sensorListTmp[sensorId].update({'temperature': toTemperature(element[elementId][1])})

def readTank (sensorId, elementId):
    sensorListTmp[sensorId].update({'currentLevel': element[elementId][0] / float(1000)})
    sensorListTmp[sensorId].update({'currentVolume': element[elementId][1] / float(10000)})

def readBatt(sensorId, elementId):
    stateOfCharge = float("%.2f" % (element[elementId][0] / 16000.0))
    sensorListTmp[sensorId].update({'stateOfCharge': stateOfCharge })
    sensorListTmp[sensorId].update({'capacity.remaining': element[elementId][1] * stateOfCharge })
    sensorListTmp[sensorId].update({'voltage': element[elementId + 2 ][1] / float(1000)})
    current = element[elementId + 1][1]
    if (current > 25000):
      current = (65535 - current) / float(100)
    else:
      current = current / float(100) * -1
    sensorListTmp[sensorId].update({'current': current})
    stateOfCharge = float("%.2f" % (element[elementId][0] / 16000.0))
    if (element[elementId][0] != 65535):
      timeRemaining = round(sensorList[sensorId]['capacity.nominal'] / 12 / ((current * stateOfCharge) + 0.001) )
      if (timeRemaining < 0):
        timeRemaining = 60*60 * 24 * 7    # One week
      sensorListTmp[sensorId].update({'capacity.timeRemaining': timeRemaining})

def readVolt (sensorId, elementId):
    sensorListTmp[sensorId].update({'voltage': element[elementId][1] / float(1000)})

def readOhm (sensorId, elementId):
    sensorListTmp[sensorId].update({'ohm': element[elementId][1] })

def readCurrent (sensorId, elementId):
    current = element[elementId][1]
    if (current > 25000):
      current = (65535 - current) / float(100)
    else:
      current = current / float(100) * -1
    sensorListTmp[sensorId].update({'current': current})

# Main loop
while True:
    updates = []
    sensorListTmp = copy.deepcopy(sensorList)

    message = ''
    while True:
      message, addr = client.recvfrom(2048)
      debug ("Received packet with length " + str(len(message)))
      if len(message) > 100 and len(message) < 1000:
        break



    # if responses[0] == '':
      # get_pico_config(addr[0])

    response = BinToHex(message)
    # debug(response)
    # if len(message) > 300:
      # debug( response

    if response[18] == 'b':
      if len(response) == 0:
        continue
      else:
        pos = 0

    element = parseResponse(response)
    # element = {0: [25615, 43879], 1: [25615, 47479], 2: [65535, 64534], 3: [1, 31679], 4: [0, 153], 5: [0, 12114], 9: [25606, 10664], 10: [65535, 64534], 11: [65535, 64980], 12: [0, 5875], 13: [0, 12672], 14: [0, 0], 15: [0, 65535], 16: [0, 65535], 17: [0, 65535], 18: [65535, 65520], 19: [65531, 34426], 20: [0, 0], 21: [0, 16], 22: [65535, 65535], 23: [65535, 65450], 24: [65535, 65048], 25: [65515, 983], 26: [0, 0], 27: [0, 0], 28: [0, 0], 29: [0, 65535], 30: [0, 65535], 31: [0, 65535], 32: [0, 65535], 33: [0, 0], 34: [65535, 65532], 35: [0, 18386], 36: [0, 26940], 37: [0, 0], 38: [0, 65535], 39: [0, 65535], 40: [0, 65535], 41: [0, 0], 42: [65529, 51037], 43: [65535, 65529], 44: [4, 9403], 45: [0, 0], 46: [65533, 6493], 47: [0, 0], 48: [65535, 18413], 49: [0, 0], 50: [15776, 53404], 51: [65535, 64980], 52: [0, 12672], 53: [32767, 65535], 54: [65531, 42226], 55: [15984, 17996], 56: [65535, 65532], 57: [0, 26940], 58: [32767, 65535], 59: [65253, 37546], 60: [0, 0], 61: [0, 0], 62: [0, 0], 63: [0, 54], 64: [0, 57], 65: [0, 65535], 66: [0, 44], 67: [0, 0], 68: [282, 2829], 69: [5, 58], 70: [300, 3000]}
    debug(element)
    for diff in list(dictdiffer.diff(old_element, element)):
      debug( diff )
    old_element = copy.deepcopy(element)

    # Add values to sensorList copy

    # Barometer
    readBaro (5, 3)
    # Pico internal
    readVolt (6, 5)

    for item in sensorList:
        # debug("sensorList[" + str(item) + "]: " + sensorList[item]["name"])
        elId = sensorList[item]['pos']
        itemType = sensorList[item]['type']
        if (itemType == 'thermometer'):
            readTemp(item, elId)
        if (itemType == 'battery'):
            readBatt(item, elId)
        if (itemType == 'ohm'):
            readOhm(item, elId)
        if (itemType == 'volt'):
            readVolt(item, elId)
        if (itemType == 'current'):
            readCurrent(item, elId)
        if (itemType == 'tank'):
            readTank(item, elId)

    # Populate JSON
    batteryInstance = 1
    currentInstance = 1
    ohmInstance = 1
    voltInstance = 0
    tankInstance = 1
    for key, value in sensorListTmp.items():
      if (value['type'] == 'barometer'):
        updates.append({"path": "environment.inside.pressure", "value": value['pressure']})
      if (value['type'] == 'thermometer'):
        updates.append({"path": "electrical.batteries.1.temperature", "value": value['temperature']})
      if (value['type'] == 'volt'):
        updates.append({"path": "electrical.volt." + str(voltInstance) + ".value", "value": value['voltage']})
        updates.append({"path": "electrical.volt." + str(voltInstance) + ".name", "value": value['name']})
        voltInstance += 1
      if (value['type'] == 'ohm'):
        updates.append({"path": "electrical.ohm." + str(ohmInstance) + ".value", "value": value['ohm']})
        updates.append({"path": "electrical.ohm." + str(ohmInstance) + ".name", "value": value['name']})
      if (value['type'] == 'current'):
        updates.append({"path": "electrical.current." + str(currentInstance) + ".value", "value": value['current']})
        updates.append({"path": "electrical.current." + str(currentInstance) + ".name", "value": value['name']})
        currentInstance += 1
      if (value['type'] == 'battery'):
        updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".name", "value": value['name']})
        updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".capacity.nominal", "value": value['capacity.nominal']})
        if 'voltage' in value:
          updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".voltage", "value": value['voltage']})
        if 'temperature' in value:
          updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".temperature", "value": value['temperature']})
        if 'current' in value:
          updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".current", "value": value['current']})
        if 'capacity.remaining' in value:
          updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".capacity.remaining", "value": value['capacity.remaining']})
          updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".stateOfCharge", "value": value['stateOfCharge']})
        if 'capacity.timeRemaining' in value:
          updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".capacity.timeRemaining", "value": value['capacity.timeRemaining']})
        batteryInstance += 1
      if (value['type'] == 'tank'):
        updates.append({"path": "tanks." + value['fluid'] + "." + str(tankInstance) + ".currentLevel", "value": value['currentLevel']})
        updates.append({"path": "tanks." + value['fluid'] + "." + str(tankInstance) + ".currentVolume", "value": value['currentVolume']})
        updates.append({"path": "tanks." + value['fluid'] + "." + str(tankInstance) + ".name", "value": value['name']})
        updates.append({"path": "tanks." + value['fluid'] + "." + str(tankInstance) + ".type", "value": value['fluid_type']})
        updates.append({"path": "tanks." + value['fluid'] + "." + str(tankInstance) + ".capacity", "value": value['capacity']})
        tankInstance += 1


    delta = {
        "updates": [
              {
                "source": {
                    "label": "Simarine Pico (" + pico_ip + ")"
                },
                "values": updates
            }
        ]
    }
    print (json.dumps(delta, indent=2))
    sys.stdout.flush()
    time.sleep (0.9)
    empty_socket(client)
