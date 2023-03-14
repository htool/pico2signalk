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
            let updates = JSON.parse(line)
            for (const [key, value] of Object.entries(updates.updates[0].values)) {
              app.debug(`${key}: ${value.path}`);
              if (updates.updates[0].values[key].path.startsWith('electrical.batteries.')) {
                let [e, b, instance, value] = updates.updates[0].values[key].path.split('.')
                instance = Number(Number(instance) + options.batteryNr - 1)
                updates.updates[0].values[key].path = [e, b, String(instance), value].join('.')
              }
              if (updates.updates[0].values[key].path.startsWith('tanks.')) {
                let [t, type, instance, value] = updates.updates[0].values[key].path.split('.')
                instance = Number(Number(instance) + options.tankNr - 1)
                updates.updates[0].values[key].path = [t, type, String(instance), value].join('.')
              }
            }
            app.debug('updates: %j', updates)
            app.handleMessage(plugin.id, updates)
          }
        })
      } catch (e) {
        console.error(e.message)
      }
    });

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
