# Pico2SignalK

Reads Simarine Pico config and values and insert them into SignalK

## Dump Pico config

To dump the sensor config as JSON without running SignalK:

```bash
node bin/dump-pico-config.js
# or, after npm install -g:
dump-pico-config --pretty
```

Set `PICO_IP=x.x.x.x` to skip UDP discovery. Set `DEBUG=pico` to log discovery and retry details to stderr.

## Plugin options

You can set the start instances of batteries, tanks etc here.
