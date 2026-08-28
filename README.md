# Pico2SignalK

Reads Simarine Pico config and values and insert them into SignalK

## Dump Pico config

To dump the sensor config as JSON without running SignalK:

```bash
node bin/dump-pico-config.js
# or, after npm install -g:
dump-pico-config --pretty
```

Set `PICO_IP=x.x.x.x` to skip UDP discovery. Set `DEBUG=pico` to log discovery, TCP send/receive, and retry details to stderr.

Optional tuning:

- `PICO_TCP_TIMEOUT_MS=30000` — per-request TCP read timeout
- `PICO_CONFIG_RETRY_MS=30000` — delay between config fetch retries

## Plugin options

You can set the start instances of batteries, tanks etc here.
