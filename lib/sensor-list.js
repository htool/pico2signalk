'use strict';

function createSensorList(config) {
  const sensorList = {};
  const fluid = ['Unknown', 'freshWater', 'fuel', 'wasteWater'];
  const fluidType = ['Unknown', 'fresh water', 'diesel', 'blackwater'];
  let elementPos = 0;

  for (const entry of Object.keys(config)) {
    const id = config[entry][0][1];
    let type = config[entry][1][1];
    let elementSize = 1;

    sensorList[id] = {};

    if (type === 0) {
      type = 'null';
      elementSize = 0;
    }
    if (type === 1) {
      type = 'volt';
      sensorList[id].name = config[entry][3];
      if (config[entry][3] === 'PICO INTERNAL') {
        elementSize = 6;
      }
    }
    if (type === 2) {
      type = 'current';
      sensorList[id].name = config[entry][3];
      elementSize = 2;
    }
    if (type === 3) {
      type = 'thermometer';
      sensorList[id].name = config[entry][3];
    }
    if (type === 5) {
      type = 'barometer';
      sensorList[id].name = config[entry][3];
      elementSize = 2;
    }
    if (type === 6) {
      type = 'ohm';
      sensorList[id].name = config[entry][3];
    }
    if (type === 8) {
      type = 'tank';
      sensorList[id].name = config[entry][3];
      sensorList[id].capacity = config[entry][7][1] / 10;
      sensorList[id].fluid_type = fluidType[config[entry][6][1]];
      sensorList[id].fluid = fluid[config[entry][6][1]];
    }
    if (type === 9) {
      type = 'battery';
      sensorList[id].name = config[entry][3];
      sensorList[id]['capacity.nominal'] = config[entry][5][1] * 36 * 12;
      elementSize = 5;
    }
    if (type === 14) {
      type = 'XX';
      elementSize = 1;
    }

    sensorList[id].type = type;
    sensorList[id].pos = elementPos;
    elementPos += elementSize;
  }

  return sensorList;
}

module.exports = {
  createSensorList,
};
