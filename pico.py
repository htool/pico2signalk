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

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def debug(string):
    if os.environ.has_key('DEBUG'):
      if os.environ['DEBUG'] == 'pico':
        print string
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
    hex = x.encode('hex')
    response = response + hex + ' '
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
    debug( "Connection to " + pico_ip + ":5001 failed. Retrying in 1 sec.")
    time.sleep(1)
    # try again
    return open_tcp(pico_ip)

def get_pico_config(pico_ip):
  config = {}
  open_tcp(pico_ip)
  response_list = []
  fluid = ['fresh water','diesel']
  fluid_type = ['freshWater','fuel']
  message = ('00 00 00 00 00 ff 02 04 8c 55 4b 00 03 ff')
  message = add_crc(message)
  response = send_receive(message)
  debug( "Response: " + response)
  # Response: 00 00 00 00 00 ff 02 04 8c 55 4b 00 11 ff 01 01 00 00 00 1e ff 02 01 00 00 00 30 ff 32 cf
  req_count = int(response.split()[19], 16) + 1
  debug( "req_count: " + str(req_count))

  for pos in range(req_count):
    message = ('00 00 00 00 00 ff 41 04 8c 55 4b 00 16 ff 00 01 00 00 00 ' + "%02x" % pos + ' ff 01 03 00 00 00 00 ff 00 00 00 00 ff')
    message = add_crc(message)
    response = send_receive(message)
    element = parseResponse(response)
    config[pos] = element

  # Close tcp connection
  s.close()
  return config

def createSensorList (config):
  sensorList = {}
  fluid = ['Unknown', 'freshWater', 'fuel']
  fluid_type = ['Unknown', 'fresh water', 'diesel']
  for entry in config.keys():
    # debug( config[entry])
    # Set id
    id = config[entry][0][1]
    # Set type
    type = config[entry][1][1]
    sensorList[id] = {}
    if (type == 3):
      type = 'thermometer'
      sensorList[id].update ({'name': config[entry][3]})
    if (type == 5):
      type = 'barometer'
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
    sensorList[id].update ({'type': type})
  return sensorList

config = get_pico_config('192.168.4.225')
debug( config)

# sensorList = {}
sensorList = createSensorList(config)
debug( sensorList)

# exit(0)

debug( "Start UDP listener")
# Setup UDP broadcasting listener
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
client.bind(("", 43210))

responseB = [''] * 50
responseC = []

old_element = {} 

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
    debug(response)
    # if len(message) > 300:
      # debug( response

    if response[18] == 'b':
      if len(response) == 0:
        continue
      else:
        pos = 0

    element = parseResponse(response)
    debug(element)
    for diff in list(dictdiffer.diff(old_element, element)):         
      debug( diff )
    old_element = copy.deepcopy(element)

    # Add values to sensorList copy

    # Barometer
    sensorListTmp_id = 5
    element_id = 3
    sensorListTmp[sensorListTmp_id].update({'pressure': element[element_id][1] + 65536})

    # Kajuit
    sensorListTmp_id = 22
    element_id = 24
    sensorListTmp[sensorListTmp_id].update({'temperature': float(("%.2f" % round(element[element_id][1] / float(10) + 273.15, 2)))})

    # Tank achter
    sensorListTmp_id = 23
    element_id = 25
    sensorListTmp[sensorListTmp_id].update({'currentLevel': element[element_id][0] / float(1000)})
    sensorListTmp[sensorListTmp_id].update({'currentVolume': element[element_id][1] / float(10000)})

    # Service accu 
    sensorListTmp_id = 24
    element_id = 26
    stateOfCharge = float("%.2f" % (element[element_id][0] / 16000.0))
    debug("Service %: " + str(stateOfCharge))
    sensorListTmp[sensorListTmp_id].update({'stateOfCharge': stateOfCharge })
    sensorListTmp[sensorListTmp_id].update({'capacity.remaining': element[element_id][1] * stateOfCharge })
    sensorListTmp[sensorListTmp_id].update({'capacity.timeRemaining': round(((element[element_id][1] * 3600) / element[element_id + 1][1]) * stateOfCharge) })
    sensorListTmp[sensorListTmp_id].update({'current': element[element_id + 1][1] / float(100)})
    sensorListTmp[sensorListTmp_id].update({'voltage': element[element_id + 2 ][1] / float(1000)})
    # Temperature Service
    # sensorListTmp_id = 25
    element_id = 31
    # debug("Temp service: " + str(float(("%.2f" % round(element[element_id][1] / float(10) + 273.15, 2)))))
    sensorListTmp[sensorListTmp_id].update({'temperature': float(("%.2f" % round(element[element_id][1] / float(10) + 273.15, 2)))})
    
    # Start accu
    sensorListTmp_id = 26
    element_id = 32
    stateOfCharge = float("%.2f" % (element[element_id][0] / 16000.0))
    debug("Start %: " + str(stateOfCharge))
    sensorListTmp[sensorListTmp_id].update({'stateOfCharge': stateOfCharge })
    sensorListTmp[sensorListTmp_id].update({'capacity.remaining': element[element_id][1] * stateOfCharge })
    sensorListTmp[sensorListTmp_id].update({'voltage': element[element_id + 2 ][1] / float(1000)})
    # sensorListTmp[sensorListTmp_id].update({'temperature': float(("%.2f" % round(element[48][1] / float(10) + 273.15, 2)))})

    # Boegschroef accu
    sensorListTmp_id = 27
    element_id = 37
    stateOfCharge = float("%.2f" % (element[element_id][0] / 16000.0))
    debug("Boegschroef %: " + str(stateOfCharge))
    sensorListTmp[sensorListTmp_id].update({'stateOfCharge': stateOfCharge })
    sensorListTmp[sensorListTmp_id].update({'capacity.remaining': element[element_id][1] * stateOfCharge })
    sensorListTmp[sensorListTmp_id].update({'voltage': element[element_id + 2 ][1] / float(1000)})
    #sensorListTmp[sensorListTmp_id].update({'temperature': float(("%.2f" % round(element[48][1] / float(10) + 273.15, 2)))})

    # Tank voor
    sensorListTmp_id = 28
    element_id = 42
    sensorListTmp[sensorListTmp_id].update({'currentLevel': element[element_id][0] / float(1000)})
    sensorListTmp[sensorListTmp_id].update({'currentVolume': element[element_id][1] / float(10000)})

    # Tank diesel
    sensorListTmp_id = 29
    element_id = 43
    sensorListTmp[sensorListTmp_id].update({'currentLevel': element[element_id][0] / float(1000)})
    sensorListTmp[sensorListTmp_id].update({'currentVolume': element[element_id][1] / float(10000)})


    # Ankerlier accu
    # element_id = 42
    # sensorListTmp_id = 30
    # if (element[element_id][0] == 16000):
      # sensorListTmp[sensorListTmp_id].update({'capacity.remaining': element[element_id][1] * 36 * 12})
      # sensorListTmp[sensorListTmp_id].update({'stateOfCharge': round(element[element_id][1] * 36 * 12 / sensorListTmp[sensorListTmp_id]['capacity.nominal']) })
    # sensorListTmp[sensorListTmp_id].update({'stateOfCharge': element[element_id + 2 ][0] / float(1000)})
    # sensorListTmp[sensorListTmp_id].update({'voltage': element[element_id + 2 ][0] / float(1000)})
    #sensorListTmp[sensorListTmp_id].update({'temperature': float(("%.2f" % round(element[48][1] / float(10) + 273.15, 2)))})
    debug( sensorListTmp )

    # Populate JSON
    batteryInstance = 1
    tankInstance = 1
    for key, value in sensorListTmp.items():
      if (value['type'] == 'battery'):
        updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".name", "value": value['name']})
        updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".capacity.nominal", "value": value['capacity.nominal']})
        if value.has_key('voltage'):
          updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".voltage", "value": value['voltage']})
        if value.has_key('temperature'):
          updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".temperature", "value": value['temperature']})
        if value.has_key('current'):
          updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".current", "value": value['current']})
        if value.has_key('capacity.remaining'):
          updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".capacity.remaining", "value": value['capacity.remaining']})
          updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".stateOfCharge", "value": value['stateOfCharge']})
        if value.has_key('capacity.timeRemaining'):
          updates.append({"path": "electrical.batteries." + str(batteryInstance) + ".capacity.timeRemaining", "value": value['capacity.timeRemaining']})
        batteryInstance += 1
      if (value['type'] == 'barometer'):
        updates.append({"path": "environment.inside.pressure", "value": value['pressure']}) 
        updates.append({"path": "environment.outside.pressure", "value": value['pressure']}) # assuming same pressure in the boat as outside
      if (value['type'] == 'thermometer' and value['name'] == 'Kajuit'):
        updates.append({"path": "environment.inside.temperature", "value": value['temperature']})
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
                    "label": "Simarine Pico"
                },
                "values": updates
            }
        ]
    }
    print json.dumps(delta)
    sys.stdout.flush()
    time.sleep (0.9)
    empty_socket(client)
