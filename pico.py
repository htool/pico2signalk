#!/usr/bin/python

import time
import socket
import sys 
import select
import requests
import json

responses14 = [''] * 26
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

def get_pico_config(pico_ip):
  # Create a TCP stream socket with address family of IPv4 (INET)
  serverport = 5001
  # Connect to the server at given IP and port
  s.connect((pico_ip, serverport))

  # CRC checksums (due to lack of knowing how to calculate these)
  CRCs14 = ('e8 19','3c 33','51 c4','85 ee','8a 2a','5e 00','33 f7','e7 dd','2c 7f','f8 55','95 a2','41 88','4e 4c','9a 66','f7 91','23 bb','71 5c','a5 76','c8 81','1c ab','13 6f')
  response_list14 = []
  pos = 0
  for crc in CRCs14:
    message = ('00 00 00 00 00 ff 41 04 8c 55 4b 00 16 ff 00 01 00 00 00 ' + "%02x" % pos + ' ff 01 03 00 00 00 00 ff 00 00 00 00 ff ' + crc)
    response = send_receive(message)
    if response != '':
      response_list14 = parse(response)
    if len(response_list14) > 6:
       responses14[pos] = response_list14[7].replace(' ','').decode('hex')
    pos += 1

  # Close tcp connection
  s.close()


# Setup UDP broadcasting listener
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
client.bind(("", 43210))

responseB = [''] * 26
responseC = []

voltage = ''
pressure = ''
temp = ''
tank1Percent = ''

while True:
    updates =[]
    message, addr = client.recvfrom(1024)
    if responses14[0] == '':
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
        while len(response) > 17:
	  part = response[0:18]
	  response = response[21:]
          pos = int(part[0:2], 16)
	  # print "pos: " + str(pos) + "  part: " + part + "   response: " + response
	  part = part[6:].replace(' ','')
          if pos != 44:
	    if responseB[pos] != part:
              # print "New B(" + str(pos) + " - " + responses14[pos-1] + "): " + str(part) + " was: " + str(responseB[pos])
	      if pos == 5:
	      	voltage = int(part, 16) / float(1000)
	      #	print responses14[pos-1] + " " + voltage + ' volt'
	      # if pos == 14:
	      #	print responses14[pos-1] + " " + str(int(part,16)) + ' Ohm'
	      if pos == 3:
		pressure = int(part[4:8],16) + 65536
		#print responses14[pos-1] + " " + pressure + ' mBar'
	      if pos == 19:
		temp = int(part,16) / float(10) + 273.15
		# print responses14[pos-1] + " " + str(temp) + ' K'
	      if pos == 20:
		tank1Percent = (int(part[1:4],16) / float(1000))
		tank1Liter = (int(part[4:8],16) / float(10000))
		#print responses14[pos-1] + " " + str(int(part[1:4],16) / float(10)) + '%' + "  " + str(int(part[4:8],16) / float(10)) + ' liter'
		#updates.append({"path": "environment.inside.temperature", "value": temp})
	      #if pos == 21:
		#print responses14[pos-1] + " " + str(int(part[1:4],16) / float(10)) + '%' + "  " + str(int(part[4:8],16) / float(10)) + ' liter'
              responseB[pos] = part
	  pos += 1
	if tank1Percent != '':
	  updates.append({"path": "tanks.freshWater.1.name", "value": 'Front'})
	  updates.append({"path": "tanks.freshWater.1.type", "value": 'fresh water'})
	  updates.append({"path": "tanks.freshWater.1.capacity", "value": 300})
	  updates.append({"path": "tanks.freshWater.1.currentLevel", "value": tank1Percent})
	  updates.append({"path": "tanks.freshWater.1.currentVolume", "value": tank1Liter})
	if pressure != '':
	  updates.append({"path": "environment.outside.pressure", "value": pressure})
	if voltage != '':
	  updates.append({"path": "electrical.batteries.1.name", "value": 'Service'})
	  updates.append({"path": "electrical.batteries.1.voltage", "value": voltage})
	  if temp != '':
	    updates.append({"path": "electrical.batteries.1.temperature", "value": temp})
	if temp != '':
	  updates.append({"path": "environment.inside.temperature", "value": temp})


#    elif response[18] == 'c':
#      if len(responseC) == 0:
#	responseC = parse(response)
#      else:
#	pos = 0
#        for part in parse(response):
#	  if responseC[pos] != part:
#	    # print "New C(" + str(pos) + "): " + str(part) + " was: " + str(responseC[pos])
#            responseC[pos] = part
#	  pos += 1

    sys.stdout.flush()

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
    time.sleep (5)
    empty_socket(client)
