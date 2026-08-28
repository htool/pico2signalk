'use strict';

const assert = require('assert');
const { hexdump, addCrc } = require('../lib/pico-protocol');

const cases = [
  [0xa8c0, 'a8 c0'],
  [0x32cf, '32 cf'],
  [0xcf, '00 cf'],
  [0x32, '00 32'],
  [0x0ce7, '0c e7'],
  [0x00, '00 00'],
];

for (const [value, expected] of cases) {
  assert.strictEqual(hexdump(value), expected, `hexdump(${value.toString(16)})`);
}

const pos26 = addCrc(
  '00 00 00 00 00 ff 41 04 8c 55 4b 00 16 ff 00 01 00 00 00 1a ff 01 03 00 00 00 00 ff 00 00 00 00 ff'
);
assert.strictEqual(pos26.endsWith('0c e7'), true, `pos26 crc: ${pos26}`);
assert.strictEqual(pos26.replace(/ /g, '').length % 2, 0);
assert.strictEqual(Buffer.from(pos26.replace(/ /g, ''), 'hex').length, 35);

console.log('hexdump tests passed');
