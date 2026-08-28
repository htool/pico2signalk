#!/usr/bin/env node
'use strict';

const { getPicoConfig, isDebugEnabled } = require('../lib/get-pico-config');

const args = process.argv.slice(2);
const pretty = args.includes('--pretty');
const raw = args.includes('--raw');

if (args.includes('--help') || args.includes('-h')) {
  console.log(`Usage: dump-pico-config [options]

Discover a Simarine Pico on the network, query its sensor config, and print JSON.

Options:
  --pretty    Pretty-print JSON output
  --raw       Include picoIp and raw TCP config alongside sensorList
  -h, --help  Show this help

Environment:
  DEBUG=pico              Log discovery, TCP, and retry details to stderr
  PICO_IP=x.x.x.x         Skip UDP discovery and use this Pico address
  PICO_TCP_TIMEOUT_MS=30000   TCP read timeout per request (default 30s)
  PICO_CONFIG_RETRY_MS=30000    Delay between config fetch retries (default 30s)
`);
  process.exit(0);
}

getPicoConfig({
  debug: isDebugEnabled() ? (msg) => console.error(msg) : () => {},
})
  .then(({ picoIp, config, sensorList }) => {
    const output = raw ? { picoIp, config, sensorList } : sensorList;
    console.log(JSON.stringify(output, null, pretty ? 2 : undefined));
  })
  .catch((err) => {
    console.error(err.message);
    process.exit(1);
  });
