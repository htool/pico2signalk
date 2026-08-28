# Pico2SignalK

Reads Simarine Pico config and values and inserts them into SignalK.

This plugin is **Node.js only** — no Python runtime required. See [CHANGELOG.md](./CHANGELOG.md)
for migration notes and command-line testing instructions.

## Test from the command line

To verify Pico connectivity and dump the sensor config without SignalK:

```bash
node bin/dump-pico-config.js --pretty
```

With debug logging:

```bash
DEBUG=pico node bin/dump-pico-config.js --raw
```

Set `PICO_IP=x.x.x.x` to skip UDP discovery. Full options and environment
variables are documented in [CHANGELOG.md](./CHANGELOG.md).

## Plugin options

You can set the start instances of batteries, tanks, etc. in the SignalK plugin
config UI.
