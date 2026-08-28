'use strict';

const dgram = require('dgram');
const { getPicoConfigTcp } = require('./pico-protocol');
const { createSensorList } = require('./sensor-list');

const UDP_PORT = 43210;

function isDebugEnabled() {
  return process.env.DEBUG === 'pico';
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function createDiscoverySocket() {
  return new Promise((resolve, reject) => {
    const socket = dgram.createSocket({ type: 'udp4', reuseAddr: true });

    socket.once('error', reject);
    socket.bind(UDP_PORT, () => {
      socket.setBroadcast(true);
      resolve(socket);
    });
  });
}

function waitForBroadcast(socket, timeoutMs = null) {
  return new Promise((resolve, reject) => {
    let timer;

    function cleanup() {
      if (timer) {
        clearTimeout(timer);
      }
      socket.removeListener('message', onMessage);
      socket.removeListener('error', onError);
    }

    function onMessage(_msg, addr) {
      cleanup();
      resolve(addr.address);
    }

    function onError(err) {
      cleanup();
      reject(err);
    }

    socket.once('message', onMessage);
    socket.once('error', onError);

    if (timeoutMs !== null) {
      timer = setTimeout(() => {
        cleanup();
        reject(new Error('timed out waiting for Pico broadcast'));
      }, timeoutMs);
    }
  });
}

async function getPicoConfig(options = {}) {
  const {
    picoIp: providedIp = process.env.PICO_IP,
    retryDelayMs = 30000,
    debug = isDebugEnabled() ? (msg) => console.error(msg) : () => {},
  } = options;

  let picoIp = providedIp || null;
  let discoverySocket = null;

  if (!picoIp) {
    debug('Start UDP listener');
    discoverySocket = await createDiscoverySocket();
    picoIp = await waitForBroadcast(discoverySocket);
    debug(`See Pico at ${picoIp}`);
  }

  let attempt = 0;
  while (true) {
    attempt += 1;
    if (attempt > 1) {
      debug(`Config retry attempt ${attempt} (waited ${retryDelayMs / 1000} s)`);
      if (discoverySocket) {
        try {
          const newIp = await waitForBroadcast(discoverySocket, 60000);
          if (newIp !== picoIp) {
            debug(`Pico IP changed: ${picoIp} -> ${newIp}`);
            picoIp = newIp;
          }
        } catch (err) {
          debug(`refresh recvfrom failed: ${err.message}`);
        }
      }
      await sleep(retryDelayMs);
    }

    const config = await getPicoConfigTcp(picoIp, { debug });
    if (config) {
      try {
        const sensorList = createSensorList(config);
        if (discoverySocket) {
          discoverySocket.close();
        }
        debug('CONFIG:');
        debug(JSON.stringify(config));
        debug('SensorList:');
        debug(JSON.stringify(sensorList));
        return { picoIp, config, sensorList };
      } catch (err) {
        debug(`createSensorList failed: ${err.message}`);
      }
    }
  }
}

module.exports = {
  createDiscoverySocket,
  getPicoConfig,
  isDebugEnabled,
  waitForBroadcast,
};
