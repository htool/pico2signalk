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
  if (hex.length === 3) {
    hex = '0' + hex;
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

function bufferToHex(buffer) {
  return Array.from(buffer, (byte) => byte.toString(16).padStart(2, '0')).join(' ');
}

function addCrc(message) {
  const fields = message.split(/\s+/);
  const messageInt = fields.slice(1).map((x) => parseInt(x, 16));
  const crcInt = calcRevCrc16(messageInt.slice(0, -1));
  return message + ' ' + hexdump(crcInt);
}

function sendReceive(socket, message, options = {}) {
  const {
    debug = () => {},
    responseTimeoutMs = parseInt(process.env.PICO_TCP_TIMEOUT_MS || '30000', 10),
    label = 'request',
  } = options;

  return new Promise((resolve, reject) => {
    const buffer = Buffer.from(message.replace(/ /g, ''), 'hex');
    let response = '';
    let settled = false;

    function finish(err, value) {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      if (err) {
        reject(err);
      } else {
        resolve(value);
      }
    }

    function onData(chunk) {
      for (const byte of chunk) {
        response += byte.toString(16).padStart(2, '0') + ' ';
      }
      debug(`TCP ${label}: received ${chunk.length} bytes (${response.trim().split(/\s+/).length} total)`);
      debug(`TCP ${label}: response ${response.trim()}`);
      finish(null, response);
    }

    function onError(err) {
      debug(`TCP ${label}: socket error ${err.message}`);
      finish(err);
    }

    function onClose(hadError) {
      if (response.length > 0) {
        debug(`TCP ${label}: connection closed after partial response (${response.trim().split(/\s+/).length} bytes)`);
        finish(null, response);
        return;
      }
      debug(`TCP ${label}: connection closed before response${hadError ? ' (with error)' : ''}`);
      finish(new Error(`connection closed before TCP response (${label})`));
    }

    function onTimeout() {
      debug(`TCP ${label}: read timeout after ${responseTimeoutMs}ms`);
      finish(new Error(`timed out waiting for TCP response (${label}, ${responseTimeoutMs}ms)`));
    }

    function cleanup() {
      clearTimeout(timeout);
      socket.setTimeout(0);
      socket.removeListener('data', onData);
      socket.removeListener('error', onError);
      socket.removeListener('close', onClose);
      socket.removeListener('timeout', onTimeout);
    }

    const timeout = setTimeout(onTimeout, responseTimeoutMs);
    socket.setTimeout(responseTimeoutMs);
    socket.on('data', onData);
    socket.once('error', onError);
    socket.once('close', onClose);
    socket.once('timeout', onTimeout);

    debug(`TCP ${label}: sending ${buffer.length} bytes`);
    debug(`TCP ${label}: message ${message}`);

    const hexPayload = message.replace(/ /g, '');
    if (hexPayload.length % 2 !== 0) {
      finish(new Error(`invalid hex message (odd length ${hexPayload.length}): ${message}`));
      return;
    }

    const writeOk = socket.write(buffer, (err) => {
      if (err) {
        debug(`TCP ${label}: write callback error ${err.message}`);
        finish(err);
      } else {
        debug(`TCP ${label}: write flushed, waiting for response`);
      }
    });

    if (!writeOk) {
      debug(`TCP ${label}: write buffer full, waiting for drain`);
      socket.once('drain', () => {
        debug(`TCP ${label}: socket drained`);
      });
    }
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
      debug(`TCP connect attempt ${retries + 1}/${maxRetries} to ${picoIp}:${port}`);
      const socket = new net.Socket();
      socket.setNoDelay(true);

      const timeout = setTimeout(() => {
        debug(`TCP connect timeout after ${connectTimeoutMs}ms`);
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
  debug(`Opening TCP config session to ${picoIp}`);
  const socket = await openTcp(picoIp, options);
  if (!socket) {
    debug('getPicoConfigTcp: openTcp returned null (Pico TCP unresponsive)');
    return null;
  }

  const config = {};
  try {
    let message = '00 00 00 00 00 ff 02 04 8c 55 4b 00 03 ff';
    message = addCrc(message);
    debug('Querying config entry count');
    const response = await sendReceive(socket, message, { debug, label: 'config-count' });
    const fields = response.trim().split(/\s+/);
    if (fields.length < 20) {
      throw new Error(`config-count response too short (${fields.length} bytes)`);
    }
    const reqCount = parseInt(fields[19], 16) + 1;
    debug(`Config entry count: ${reqCount}`);

    for (let pos = 0; pos < reqCount; pos++) {
      message = `00 00 00 00 00 ff 41 04 8c 55 4b 00 16 ff 00 01 00 00 00 ${pos.toString(16).padStart(2, '0')} ff 01 03 00 00 00 00 ff 00 00 00 00 ff`;
      const request = addCrc(message);
      debug(`Fetching config entry ${pos + 1}/${reqCount}`);
      const entryResponse = await sendReceive(socket, request, {
        debug,
        label: `config-entry-${pos}`,
      });
      config[pos] = parseResponse(entryResponse);
      debug(`Parsed config entry ${pos}: ${Object.keys(config[pos]).length} fields`);
    }

    debug(`TCP config session complete (${reqCount} entries)`);
    return config;
  } catch (err) {
    debug(`getPicoConfigTcp failed: ${err.message}`);
    return null;
  } finally {
    debug('Closing TCP config session');
    socket.destroy();
  }
}

module.exports = {
  addCrc,
  bufferToHex,
  getNextField,
  getPicoConfigTcp,
  hexdump,
  hexToByte,
  openTcp,
  parseResponse,
  sendReceive,
};
