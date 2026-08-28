# Changelog

All notable changes to this project are documented here.

## [0.0.21] - 2026-08-28

### Changed — Node.js only

Config discovery and retrieval no longer depend on Python. The plugin and CLI
share the same Node.js implementation under `lib/`.

**Removed:**

- `pico.py` — config dumper (replaced by `lib/get-pico-config.js`)
- `brainsmoke.py` — CRC16 helper (replaced by `lib/crc16.js`)

**Added:**

- `lib/get-pico-config.js` — UDP discovery + TCP config query
- `lib/pico-protocol.js` — TCP protocol, parsing, CRC
- `lib/sensor-list.js` — sensor list builder
- `bin/dump-pico-config.js` — standalone CLI to dump config as JSON

**Requirements:** Node.js 14 or later. Python 3 is no longer required.

### Testing from the command line

From the plugin directory, with a Pico on the same network:

```bash
# Dump sensor config as JSON (stdout)
node bin/dump-pico-config.js

# Pretty-printed JSON
node bin/dump-pico-config.js --pretty

# Include Pico IP and raw TCP config
node bin/dump-pico-config.js --raw

# Skip UDP discovery when you already know the Pico IP
PICO_IP=192.168.2.5 node bin/dump-pico-config.js --pretty

# Verbose debug logging (stderr): UDP/TCP send-receive, entry progress, retries
DEBUG=pico node bin/dump-pico-config.js --raw
```

Successful output is a JSON object on stdout (sensor IDs → type, name, position,
capacity, etc.). Debug and progress messages go to stderr when `DEBUG=pico` is set.

Optional environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `PICO_IP` | _(discover via UDP)_ | Pico address; skips UDP discovery |
| `DEBUG` | _(off)_ | Set to `pico` for verbose logging |
| `PICO_TCP_TIMEOUT_MS` | `30000` | Per-request TCP read timeout |
| `PICO_CONFIG_RETRY_MS` | `30000` | Delay between config fetch retries |

Run the unit test for CRC encoding:

```bash
node test/hexdump.test.js
```

## [0.0.20] and earlier

Config was retrieved by spawning `python3 pico.py`. Live UDP value processing
was already handled in Node.js (`index.js`).
