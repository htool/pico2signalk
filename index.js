const id = "pico2signalk";
const { spawn } = require('node:child_process');

var plugin = {}

module.exports = function(app, options) {
  "use strict"
  var plugin = {}
  plugin.id = id
  plugin.name = "Simarine Pico to SignalK"
  plugin.description = "Read Simarine Pico config and updates from the network."

  var unsubscribes = []

  var schema = {
    properties: {
      batteryNr: {
        type: "number",
        title: "Set starting instance for batteries",
        default: 1
      },
      tankNr: {
        type: "number",
        title: "Set starting instance for tanks",
        default: 1
      },
      currentNr: {
        type: "number",
        title: "Set starting instance for current",
        default: 1
      },
      voltNr: {
        type: "number",
        title: "Set starting instance for voltages",
        default: 0
      },
      ohmNr: {
        type: "number",
        title: "Set starting instance for ohm",
        default: 1
      }
    }
  }

  plugin.schema = function() {
    return schema
  }

  let child

  plugin.start = function(options, restartPlugin) {
    app.debug('Starting plugin');

    var sensorList
    var configRead = false
    child = spawn('python3', ['pico.py'], { cwd: __dirname });

    child.stdout.on('data', function (data) {
      let dataString = data.toString('utf-8')
      sensorList = JSON.parse(dataString)
      app.debug('sensorList: %j', sensorList)
      configRead = true
    })

    var udp = require('dgram')
    var port = 43210
    var socket = udp.createSocket('udp4')
    var element
    var sensorListTmp
    var lastUpdate
    var firstUpdate = true

    socket.on('message', function (msg, info){
      if (Date.now() - lastUpdate < 1000) {
        // One update per second
        return
      }
      lastUpdate = Date.now()
      let message = msg.toString('hex')
      // app.debug(message)
      if (configRead == true && message.length > 100 && message.length < 1000) {
        element = parseMessage(message)
        sensorListTmp = JSON.parse(JSON.stringify(sensorList))
        Object.keys(sensorList).forEach(item => {
	        // debug("sensorList[" + str(item) + "]: " + sensorList[item]["name"])
	        let elId = sensorList[item]['pos']
	        let type = sensorList[item]['type']
          switch (type) {
	          case 'barometer':
	            readBaro(item, elId)
              break
	          case 'thermometer':
	            readTemp(item, elId)
              break
	          case 'battery':
	            readBatt(item, elId)
              break
	          case 'ohm':
	            readOhm(item, elId)
              break
	          case 'volt':
	            readVolt(item, elId)
              break
	          case 'current':
	            readCurrent(item, elId)
              break
	          case 'tank':
	            readTank(item, elId)
              break
          }
        })
        // app.debug(sensorListTmp)
        let updates = createUpdates(sensorListTmp)
        pushDelta (updates)
      } else {
        // app.debug('Not processing: ' + message)
      }
    });

    socket.on('listening', function(){
      var address = socket.address();
      app.debug("listening on :" + address.address + ":" + address.port);
    });

    socket.bind(port, function() {
      socket.setBroadcast(true);
      const address = socket.address()
      app.debug("Client using port " + address.port)
    })

    socket.on('error', function (err) {
      app.debug('Error: ' + err)
    })

    function getElement(id, pos) {
      if (typeof element[id] != 'undefined') {
        if (typeof element[id][pos] != 'undefined') {
          return element[id][pos]
        } else {
          app.debug('pos %d in element[%d] not found (%s)', pos, id, JSON.stringify(element[id]))
          return 0
        }
      } else {
        app.debug('element[%d] not found (%s)', id, JSON.stringify(element))
        return 0
      }
    }

    function readBaro (sensorId, elementId) {
      sensorListTmp[sensorId]['pressure'] = getElement(elementId, 1) + 65536
    }

    function readTemp (sensorId, elementId) {
      sensorListTmp[sensorId]['temperature'] = toTemperature(getElement(elementId, 1))
    }

    function readTank (sensorId, elementId) {
      sensorListTmp[sensorId]['currentLevel'] = getElement(elementId, 0) / 1000
      sensorListTmp[sensorId]['currentVolume'] = getElement(elementId, 1) / 1000
    }

    function readVolt (sensorId, elementId) {
      let volt = getElement(elementId, 1)
      if (volt != 65535) {
        sensorListTmp[sensorId]['voltage'] = volt / 1000
      }
    }

    function readOhm (sensorId, elementId) {
      sensorListTmp[sensorId]['ohm'] = getElement(elementId, 1)
    }

    function readCurrent (sensorId, elementId) {
      let current = getElement(elementId, 1)
      if (current > 25000) {
        current = (65535 - current) / 100
      } else {
        current = current / 100 * -1
      }
      sensorListTmp[sensorId]['current'] = current
    }

    function readBatt (sensorId, elementId) {
      let stateOfCharge = Number((getElement(elementId, 0) / 16000).toFixed(2))
      sensorListTmp[sensorId]['stateOfCharge'] = stateOfCharge
      sensorListTmp[sensorId]['capacity.remaining'] = getElement(elementId, 1) * stateOfCharge
      sensorListTmp[sensorId]['voltage'] = getElement(elementId + 2, 1) / 1000
      let current = getElement(elementId + 1, 1)
      if (current > 25000) {
        current = (65535 - current) / 100
      } else {
        current = current / 100 * -1
      }
      sensorListTmp[sensorId]['current'] = current
      let timeRemaining
      if (getElement(elementId, 0) != 65535) {
        timeRemaining = Math.round(sensorList[sensorId]['capacity.nominal'] / 12 / ((current * stateOfCharge) + 0.001) )
      }
      if (timeRemaining < 0) {
        timeRemaining = 60*60 * 24 * 7    // One week
      }
      sensorListTmp[sensorId]['capacity.timeRemaining'] = timeRemaining
    }

    function toTemperature (temp) {
      // Unsigned to signed
      if (temp > 32768) {
        temp = temp - 65536
      }
      let temp2 = Number((temp / 10 + 273.15).toFixed(2))
      return temp2
    }

    function parseMessage (hexString) {
      var result = {}
      hexString = hexString.substr(28)
      // app.debug("hexString: " + hexString)
      while (hexString.length > 4) { 
        let [field_nr, field_data, response] = getNextField(hexString)
        result[field_nr] = field_data
        hexString = response
        
      }
      return result  
    }
    
    function getNextField (hexString) {
      // app.debug("field_nr: " + hexString.substr(0,2) + " field_type: " + hexString.substr(2,2))
      let field_nr = parseInt(hexString.substr(0,2), 16)
      let field_type = parseInt(hexString.substr(2,2), 16)
      // app.debug(`field_nr: ${field_nr} field_type: ${field_type}`)
      switch (field_type) {
        case 1:
          let a = parseInt(hexString.substr(4,4), 16)
          let b = parseInt(hexString.substr(8,4), 16)
          let field_data = [a, b]
          hexString = hexString.substr(14)
          return [field_nr, field_data, hexString]
          break
        case 3:
          break
        case 4:
          // Text string
          break
      }
    }


    function pushDelta(values) {
      var update = {
        updates: [
          { 
            values: values
          }
        ]
      }
      app.debug('update: %j', update)
      app.handleMessage(plugin.id, update)
      return
    }

    function sendMetas(metas) {
      var update = {
        updates: [
          { 
            meta: metas
          }
        ]
      }
      app.debug('update: %j', update)
      app.handleMessage(plugin.id, update)
      return
    }

    function createUpdates (sensorList) {
	    var batteryInstance = options.batteryNr || 1
	    var currentInstance = options.currentNr || 1
	    var ohmInstance = options.ohmNr || 1
	    var voltInstance = options.voltNr || 0
	    var tankInstance = options.tankNr || 1
	    // for key, value in sensorList.items():
      var updates = []
      var metas = []
      for (const [key, value] of Object.entries(sensorList)) {
        // app.debug('key: %d  value: %j', key, value)
        switch (value['type']) {
	        case 'barometer':
	          updates.push({"path": "environment.inside.pressure", "value": value.pressure})
            break
	        case 'thermometer':
	          updates.push({"path": "electrical.batteries.1.temperature", "value": value.temperature})
            break
	        case 'volt':
	          updates.push({"path": "electrical.voltage." + String(voltInstance) + ".value", "value": value.voltage})
	          updates.push({"path": "electrical.voltage." + String(voltInstance) + ".name", "value": value.name})
            if (firstUpdate) {
	            metas.push({"path": "electrical.voltage." + String(voltInstance) + ".value", "value": {"units": "V"}})
            }
	          voltInstance++
            break
	        case 'ohm':
	          updates.push({"path": "electrical.ohm." + String(ohmInstance) + ".value", "value": value.ohm})
	          updates.push({"path": "electrical.ohm." + String(ohmInstance) + ".name", "value": value.name})
            if (firstUpdate) {
	            metas.push({"path": "electrical.ohm." + String(ohmInstance) + ".value", "value": {"units": "ohm"}})
            }
            ohmInstance++
            break
	        case 'current':
	          updates.push({"path": "electrical.current." + String(currentInstance) + ".value", "value": value.current})
	          updates.push({"path": "electrical.current." + String(currentInstance) + ".name", "value": value.name})
            if (firstUpdate) {
	            metas.push({"path": "electrical.current." + String(currentInstance) + ".value", "value": {"units": "A"}})
            }
	          currentInstance++
            break
	        case 'battery':
	          updates.push({"path": "electrical.batteries." + String(batteryInstance) + ".name", "value": value.name})
	          updates.push({"path": "electrical.batteries." + String(batteryInstance) + ".capacity.nominal", "value": value['capacity.nominal']})
	          if (value.hasOwnProperty('voltage')) {
	            updates.push({"path": "electrical.batteries." + String(batteryInstance) + ".voltage", "value": value.voltage})
            }
	          if (value.hasOwnProperty('temperature')) {
	            updates.push({"path": "electrical.batteries." + String(batteryInstance) + ".temperature", "value": value.temperature})
            }
	          if (value.hasOwnProperty('current')) {
		          updates.push({"path": "electrical.batteries." + String(batteryInstance) + ".current", "value": value.current})
            }
	          if (value.hasOwnProperty('capacity.remaining')) {
		          updates.push({"path": "electrical.batteries." + String(batteryInstance) + ".capacity.remaining", "value": value['capacity.remaining']})
		          updates.push({"path": "electrical.batteries." + String(batteryInstance) + ".capacity.stateOfCharge", "value": value.stateOfCharge})
            }
	          if (value.hasOwnProperty('capacity.timeRemaining')) {
		          updates.push({"path": "electrical.batteries." + String(batteryInstance) + ".capacity.timeRemaining", "value": value['capacity.timeRemaining']})
			        batteryInstance++
            }
            break
			    case 'tank':
			      updates.push({"path": "tanks." + value.fluid + "." + String(tankInstance) + ".currentLevel", "value": value.currentLevel})
			      updates.push({"path": "tanks." + value.fluid + "." + String(tankInstance) + ".currentVolume", "value": value.currentVolume / 10})
			      updates.push({"path": "tanks." + value.fluid + "." + String(tankInstance) + ".name", "value": value.name})
			      updates.push({"path": "tanks." + value.fluid + "." + String(tankInstance) + ".type", "value": value.fluid_type})
			      updates.push({"path": "tanks." + value.fluid + "." + String(tankInstance) + ".capacity", "value": value.capacity / 1000})
			      tankInstance++
            break
		    }
      }
      if (firstUpdate) {
        firstUpdate = false
        sendMetas(metas)
      }
      return updates
    }
  }

  plugin.stop = function() {
    if (child) {
      process.kill(child.pid)
      child = undefined
    }
    app.debug("Stopped")
  }

  return plugin;
};
