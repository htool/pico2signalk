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

    child = spawn('python', ['pico.py'], { cwd: __dirname });

    child.stdout.on('data', function (data) {
      try {
        data.toString().split(/\r?\n/).forEach(line => {
          if (line.length > 0) {
            let sensorObj = JSON.parse(line)
            app.debug('sensorList: %j', sensorObj)
            let updates = createUpdates(sensorObj)
            app.debug('updates: %j', updates)
            pushDelta(app, updates)
          }
        })
      } catch (e) {
        console.error(e.message)
      }
    });

    function pushDelta(app, values) {
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

    function createUpdates (sensorList) {
	    var batteryInstance = options.batteryNr || 1
	    var currentInstance = options.currentNr || 1
	    var ohmInstance = options.ohmNr || 1
	    var voltInstance = options.voltNr || 0
	    var tankInstance = options.tankNr || 1
	    // for key, value in sensorList.items():
      var updates = []
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
	          voltInstance++
            break
	        case 'ohm':
	          updates.push({"path": "electrical.ohm." + String(ohmInstance) + ".value", "value": value.ohm})
	          updates.push({"path": "electrical.ohm." + String(ohmInstance) + ".name", "value": value.name})
            break
	        case 'current':
	          updates.push({"path": "electrical.current." + String(currentInstance) + ".value", "value": value.current})
	          updates.push({"path": "electrical.current." + String(currentInstance) + ".name", "value": value.name})
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
		          updates.push({"path": "electrical.batteries." + String(batteryInstance) + ".stateOfCharge", "value": value.stateOfCharge})
            }
	          if (value.hasOwnProperty('capacity.timeRemaining')) {
		          updates.push({"path": "electrical.batteries." + String(batteryInstance) + ".capacity.timeRemaining", "value": value['capacity.timeRemaining']})
			        batteryInstance++
            }
            break
			    case 'tank':
			      updates.push({"path": "tanks." + value.fluid + "." + String(tankInstance) + ".currentLevel", "value": value.currentLevel})
			      updates.push({"path": "tanks." + value.fluid + "." + String(tankInstance) + ".currentVolume", "value": value.currentVolume})
			      updates.push({"path": "tanks." + value.fluid + "." + String(tankInstance) + ".name", "value": value.name})
			      updates.push({"path": "tanks." + value.fluid + "." + String(tankInstance) + ".type", "value": value.fluid_type})
			      updates.push({"path": "tanks." + value.fluid + "." + String(tankInstance) + ".capacity", "value": value.capacity})
			      tankInstance++
            break
		    }
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
