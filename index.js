const id = "Pico2SignalK";
const { spawn } = require('node:child_process');

var plugin = {}

module.exports = function(app, options) {
  "use strict"
  var plugin = {}
  plugin.id = id
  plugin.name = "Simarine Pico to SignalK"
  plugin.description = "Read Simarine Pico config and updates from the network."

  var unsubscribes = []

  plugin.schema = function() {
    return {}
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
            app.debug('update: %j', updates)
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
