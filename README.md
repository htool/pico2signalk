# Pico2SignalK
Read Simarine Pico values and insert them into SignalK

It's mostly hardcoded for my situation at the moment, but the principles are there to make it work for others.

The Pico uses a ModBus protocol which I don't fully understand. The hardcoded CRC check values come from a capture I did on my setup. Being able to generated the CRC will greatly help to simplify the code.

The code starts listening for udp data broadcasted by th Pico.
Then it will get the iriginating host and connect on tcp/5001 to get the names of the values.
This will need some rework once I have more sensors up and running.

SignalK integration based on:
  https://github.com/SignalK/sk-plugin-python-demo

This is what I added to SignalK's settings.json:

    {
      "id": "Simarine Pico",
      "pipeElements": [{
        "type": "providers/execute",
        "options": {
          "command": "python /home/pi/Pico2SignalK/pico.py"
        }
      }, {
        "type": "providers/liner"
      }, {
        "type": "providers/from_json"
      }]
    },

