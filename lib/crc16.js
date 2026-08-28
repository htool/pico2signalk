'use strict';

// CRC16 reverse-engineered by Erik Bosman / @brainsmoke

function calcRevCrc16(bytes, poly = 0x1189, start = 0x0000) {
  let crc = start;
  for (const byte of bytes) {
    let c = byte;
    for (let i = 0; i < 8; i++) {
      const cMsb = (c >> 7) & 1;
      const crcMsb = (crc >> 15) & 1;
      c = (c << 1) & 0xff;
      crc = (crc << 1) & 0xffff;
      if (cMsb ^ crcMsb) {
        crc ^= poly;
      }
    }
  }
  return crc;
}

module.exports = {
  calcRevCrc16,
};
