'use strict';

const net = require('net');
const { calcRevCrc16 } = require('./crc16');

function hexdump(byte) {
  let hex = byte.toString(16);
  if (hex.length === 1) {
    hex = '0' + hex;
  }
  if (hex.length === 2) {
    hex = '00' + hex;
  }
  return hex.slice(0, 2) + ' ' + hex.slice(2, 4);
}

function hexToByte(hexStr) {
  const bytes = [];
  const normalized = hexStr.replace(/ /g, '');
  for (let i = 0; i < normalized.length; i += 2) {
    bytes.push(String.fromCharCode(parseInt(normalized.slice(i, i + 2), 16)));
  }
  return bytes.join('');
}

function addCrc(message) {
  const fields = message.split(/\s+/);
  const messageInt = fields.slice(1).map((x) => parseInt(x, 16));
  const crcInt = calcRevCrc16(messageInt.slice(0, -1));
  return message + ' ' + hexdump(crcInt);
}

function sendReceive(socket, message) {
  return new Promise((resolve, reject) => {
    const buffer = Buffer.from(message.replace(/ /g, ''), 'hex');
    let response = '';

    function onData(chunk) {
      for (const byte of chunk) {
        response += byte.toString(16).padStart(2, '0') + ' ';
      }
      cleanup();
      resolve(response);
    }

    function onError(err) {
      cleanup();
      reject(err);
    }

    function cleanup() {
      socket.removeListener('data', onData);
      socket.removeListener('error', onError);
    }

    socket.once('data', onData);
    socket.once('error', onError);
    socket.write(buffer);
  });
}

function openTcp(picoIp, options = {}) {
  const {
    port = 5001,
    maxRetries = 5,
    retryDelayMs = 5000,
    connectTimeoutMs = 10000,
    debug = () => {},
  } = options;

  return new Promise((resolve) => {
    let retries = 0;

    function attempt() {
      const socket = new net.Socket();
      socket.setNoDelay(true);

      const timeout = setTimeout(() => {
        socket.destroy();
        onFailure(new Error('connection timeout'));
      }, connectTimeoutMs);

      socket.once('connect', () => {
        clearTimeout(timeout);
        debug(`Connected to ${picoIp}:${port}`);
        resolve(socket);
      });

      socket.once('error', (err) => {
        clearTimeout(timeout);
        onFailure(err);
      });

      socket.connect(port, picoIp);
    }

    function onFailure(err) {
      debug(`Connection attempt failed: ${err.message}`);
      retries += 1;
      if (retries < maxRetries) {
        debug(`Retrying in ${retryDelayMs / 1000} seconds...`);
        setTimeout(attempt, retryDelayMs);
      } else {
        debug(`Max retries (${maxRetries}) reached.`);
        resolve(null);
      }
    }

    attempt();
  });
}

function getNextField(response) {
  const fieldNr = parseInt(response.slice(0, 2), 16);
  const fieldType = parseInt(response.slice(3, 5), 16);

  if (fieldType === 1) {
    const data = response.slice(6, 17);
    response = response.slice(21);
    const a = parseInt(data.slice(0, 5).replace(/ /g, ''), 16);
    const b = parseInt(data.slice(6, 11).replace(/ /g, ''), 16);
    return [fieldNr, [a, b], response];
  }

  if (fieldType === 3) {
    const data = response.slice(21, 32);
    response = response.slice(36);
    if (data.slice(0, 11) === '7f ff ff ff') {
      return [fieldNr, '', response];
    }
    const a = parseInt(data.slice(0, 5).replace(/ /g, ''), 16);
    const b = parseInt(data.slice(6, 11).replace(/ /g, ''), 16);
    return [fieldNr, [a, b], response];
  }

  if (fieldType === 4) {
    response = response.slice(21);
    let nextHex = response.slice(0, 2);
    let word = '';
    while (nextHex !== '00') {
      word += nextHex;
      response = response.slice(3);
      nextHex = response.slice(0, 2);
    }
    const fieldData = hexToByte(word);
    response = response.slice(6);
    return [fieldNr, fieldData, response];
  }

  throw new Error(`Unknown field type ${fieldType}`);
}

function parseResponse(response) {
  const dict = {};
  response = response.slice(42);
  while (response.length > 6) {
    const [fieldNr, fieldData, rest] = getNextField(response);
    dict[fieldNr] = fieldData;
    response = rest;
  }
  return dict;
}

async function getPicoConfigTcp(picoIp, options = {}) {
  const { debug = () => {} } = options;
  const socket = await openTcp(picoIp, options);
  if (!socket) {
    debug('getPicoConfigTcp: openTcp returned null (Pico TCP unresponsive)');
    return null;
  }

  const config = {};
  try {
    let message = '00 00 00 00 00 ff 02 04 8c 55 4b 00 03 ff';
    message = addCrc(message);
    const response = await sendReceive(socket, message);
    const reqCount = parseInt(response.split(/\s+/)[19], 16) + 1;

    for (let pos = 0; pos < reqCount; pos++) {
      message = `00 00 00 00 00 ff 41 04 8c 55 4b 00 16 ff 00 01 00 00 00 ${pos.toString(16).padStart(2, '0')} ff 01 03 00 00 00 00 ff 00 00 00 00 ff`;
      const request = addCrc(message);
      const entryResponse = await sendReceive(socket, request);
      config[pos] = parseResponse(entryResponse);
    }

    return config;
  } catch (err) {
    debug(`getPicoConfigTcp failed: ${err.message}`);
    return null;
  } finally {
    socket.destroy();
  }
}

module.exports = {
  addCrc,
  getNextField,
  getPicoConfigTcp,
  hexdump,
  hexToByte,
  openTcp,
  parseResponse,
  sendReceive,
};
