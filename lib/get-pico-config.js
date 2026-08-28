'use strict';

const dgram = require('dgram');
const { getPicoConfigTcp } = require('./pico-protocol');
const { createSensorList } = require('./sensor-list');

const UDP_PORT = 43210;

function isDebugEnabled() {
  return process.env.DEBUG === 'pico';
}

function createDebugLogger(baseDebug) {
  return (msg) => {
    const ts = new Date().toISOString();
    baseDebug(`[${ts}] ${msg}`);
  };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function createDiscoverySocket(debug) {
  return new Promise((resolve, reject) => {
    const socket = dgram.createSocket({ type: 'udp4', reuseAddr: true });

    socket.once('error', reject);
    socket.bind(UDP_PORT, () => {
      socket.setBroadcast(true);
      const address = socket.address();
      debug(`UDP listening on ${address.address}:${address.port}`);
      resolve(socket);
    });
  });
}

function waitForBroadcast(socket, timeoutMs = null, debug = () => {}) {
  return new Promise((resolve, reject) => {
    let timer;

    function cleanup() {
      if (timer) {
        clearTimeout(timer);
      }
      socket.removeListener('message', onMessage);
      socket.removeListener('error', onError);
    }

    function onMessage(msg, addr) {
      cleanup();
      debug(`UDP broadcast from ${addr.address}:${addr.port}, ${msg.length} bytes`);
      resolve(addr.address);
    }

    function onError(err) {
      cleanup();
      reject(err);
    }

    socket.once('message', onMessage);
    socket.once('error', onError);

    if (timeoutMs !== null) {
      debug(`Waiting up to ${timeoutMs / 1000}s for Pico UDP broadcast`);
      timer = setTimeout(() => {
        cleanup();
        reject(new Error('timed out waiting for Pico broadcast'));
      }, timeoutMs);
    } else {
      debug('Waiting for Pico UDP broadcast');
    }
  });
}

async function getPicoConfig(options = {}) {
  const baseDebug = options.debug || (isDebugEnabled() ? (msg) => console.error(msg) : () => {});
  const debug = createDebugLogger(baseDebug);
  const {
    picoIp: providedIp = process.env.PICO_IP,
    retryDelayMs = parseInt(process.env.PICO_CONFIG_RETRY_MS || '30000', 10),
  } = options;

  let picoIp = providedIp || null;
  let discoverySocket = null;

  if (!picoIp) {
    debug('Start UDP listener');
    discoverySocket = await createDiscoverySocket(debug);
    picoIp = await waitForBroadcast(discoverySocket, null, debug);
    debug(`See Pico at ${picoIp}`);
  } else {
    debug(`Using provided Pico IP ${picoIp}`);
  }

  let attempt = 0;
  while (true) {
    attempt += 1;
    debug(`Config fetch attempt ${attempt}`);

    if (attempt > 1) {
      debug(`Waiting ${retryDelayMs / 1000}s before retry`);
      if (!providedIp) {
        if (!discoverySocket) {
          debug('Re-opening UDP listener for Pico IP refresh');
          discoverySocket = await createDiscoverySocket(debug);
        }
        try {
          const newIp = await waitForBroadcast(discoverySocket, 60000, debug);
          if (newIp !== picoIp) {
            debug(`Pico IP changed: ${picoIp} -> ${newIp}`);
            picoIp = newIp;
          } else {
            debug(`Pico IP unchanged (${picoIp})`);
          }
        } catch (err) {
          debug(`refresh recvfrom failed: ${err.message}`);
        }
      }
      await sleep(retryDelayMs);
    }

    if (discoverySocket) {
      debug('Closing UDP discovery socket before TCP config query');
      discoverySocket.close();
      discoverySocket = null;
    }

    const config = await getPicoConfigTcp(picoIp, { debug, ...options });
    if (config) {
      try {
        const sensorList = createSensorList(config);
        debug(`Built sensorList with ${Object.keys(sensorList).length} sensors`);
        debug('CONFIG:');
        debug(JSON.stringify(config));
        debug('SensorList:');
        debug(JSON.stringify(sensorList));
        return { picoIp, config, sensorList };
      } catch (err) {
        debug(`createSensorList failed: ${err.message}`);
      }
    } else {
      debug(`Config fetch attempt ${attempt} returned no config`);
    }
  }
}

module.exports = {
  createDiscoverySocket,
  createDebugLogger,
  getPicoConfig,
  isDebugEnabled,
  waitForBroadcast,
};
