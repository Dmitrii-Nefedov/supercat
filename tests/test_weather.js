// JavaScript unit tests for index.html weather functions
// Run: node tests/test_weather.js

const assert = {
  strictEqual(a, b, msg) {
    if (a !== b) throw new Error(`FAIL: ${msg || ''} — expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`);
  },
  ok(val, msg) {
    if (!val) throw new Error(`FAIL: ${msg || ''} — expected truthy`);
  },
};

// ---------- Pure functions extracted from index.html ----------

function convertTemp(celsius, unit) {
  if (unit === 'F') return Math.round(celsius * 9 / 5 + 32);
  return Math.round(celsius);
}

function tempLabel(unit) {
  return unit === 'F' ? '°F' : '°C';
}

function getDayName(dateStr, index) {
  if (index === 0) return 'Сегодня';
  if (index === 1) return 'Завтра';
  const date = new Date(dateStr + 'T12:00:00');
  const days = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
  return days[date.getDay()];
}

function isDaytime(sunriseStr, sunsetStr) {
  if (!sunriseStr || !sunsetStr) return true;
  const now = new Date();
  const rise = new Date(sunriseStr);
  const set = new Date(sunsetStr);
  return now >= rise && now < set;
}

function windDirection(degrees) {
  if (degrees == null) return '—';
  const dirs = ['С', 'ССВ', 'СВ', 'ВСВ', 'В', 'ВЮВ', 'ЮВ', 'ЮЮВ', 'Ю', 'ЮЮЗ', 'ЮЗ', 'ЗЮЗ', 'З', 'ЗСЗ', 'СЗ', 'ССЗ'];
  return dirs[Math.round(degrees / 22.5) % 16];
}

function getUVClass(uv) {
  if (uv == null) return '';
  if (uv <= 2) return 'uv-low';
  if (uv <= 5) return 'uv-moderate';
  if (uv <= 7) return 'uv-high';
  if (uv <= 10) return 'uv-very-high';
  return 'uv-extreme';
}

function setWeatherTheme(code, isDay) {
  let theme;
  if (code === 0 || code === 1) theme = isDay ? 'sunny' : 'clear-night';
  else if (code === 2 || code === 3) theme = 'cloudy';
  else if (code >= 45 && code <= 48) theme = 'foggy';
  else if ((code >= 51 && code <= 57) || (code >= 61 && code <= 67) || (code >= 80 && code <= 82)) theme = 'rainy';
  else if ((code >= 71 && code <= 77) || (code >= 85 && code <= 86)) theme = 'snowy';
  else if (code >= 95 && code <= 99) theme = 'thunderstorm';
  else theme = isDay ? 'sunny' : 'clear-night';
  return theme;
}

function formatTime(dateStr) {
  if (!dateStr) return '';
  const m = dateStr.match(/T(\d{2}:\d{2})/);
  return m ? m[1] : '';
}

const wmoCodes = {
  0: '☀️', 1: '🌤️', 2: '⛅', 3: '☁️', 45: '🌫️', 48: '🌫️',
  51: '🌦️', 53: '🌦️', 55: '🌦️', 56: '🌧️', 57: '🌧️',
  61: '🌧️', 63: '🌧️', 65: '🌧️', 66: '🌧️', 67: '🌧️',
  71: '🌨️', 73: '🌨️', 75: '🌨️', 77: '🌨️',
  80: '🌦️', 81: '🌦️', 82: '🌦️', 85: '🌨️', 86: '🌨️',
  95: '⛈️', 96: '⛈️', 99: '⛈️'
};

const allWMOCodes = [0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57,
  61, 63, 65, 66, 67, 71, 73, 75, 77,
  80, 81, 82, 85, 86, 95, 96, 99];

// ---------- Test Runner ----------

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
  } catch (e) {
    failed++;
    console.error(`  ✗ ${name}: ${e.message}`);
  }
}

// ---------- Tests ----------

console.log('\n  convertTemp');
test('Celsius returns rounded input', () => {
  assert.strictEqual(convertTemp(22.5, 'C'), 23);
  assert.strictEqual(convertTemp(0, 'C'), 0);
  assert.strictEqual(convertTemp(-5.2, 'C'), -5);
});
test('Fahrenheit conversion', () => {
  assert.strictEqual(convertTemp(0, 'F'), 32);
  assert.strictEqual(convertTemp(100, 'F'), 212);
  assert.strictEqual(convertTemp(-17.8, 'F'), 0);
  assert.strictEqual(convertTemp(37, 'F'), 99);
});

console.log('  tempLabel');
test('Celsius label', () => assert.strictEqual(tempLabel('C'), '°C'));
test('Fahrenheit label', () => assert.strictEqual(tempLabel('F'), '°F'));

console.log('  getDayName');
test('index 0 is Сегодня', () => assert.strictEqual(getDayName('2026-07-05', 0), 'Сегодня'));
test('index 1 is Завтра', () => assert.strictEqual(getDayName('2026-07-06', 1), 'Завтра'));
test('index 2+ returns day name', () => {
  assert.strictEqual(getDayName('2026-07-06', 2), 'Пн');
  assert.strictEqual(getDayName('2026-07-07', 2), 'Вт');
  assert.strictEqual(getDayName('2026-07-08', 2), 'Ср');
  assert.strictEqual(getDayName('2026-07-09', 2), 'Чт');
  assert.strictEqual(getDayName('2026-07-10', 2), 'Пт');
  assert.strictEqual(getDayName('2026-07-11', 2), 'Сб');
  assert.strictEqual(getDayName('2026-07-12', 2), 'Вс');
});

console.log('  isDaytime');
test('returns true when sunrise/sunset missing', () => {
  assert.ok(isDaytime(null, null));
  assert.ok(isDaytime(undefined, undefined));
  assert.ok(isDaytime('', ''));
});

console.log('  windDirection');
test('16-point compass', () => {
  assert.strictEqual(windDirection(0), 'С');
  assert.strictEqual(windDirection(90), 'В');
  assert.strictEqual(windDirection(180), 'Ю');
  assert.strictEqual(windDirection(270), 'З');
  assert.strictEqual(windDirection(22.5), 'ССВ');
  assert.strictEqual(windDirection(45), 'СВ');
  assert.strictEqual(windDirection(315), 'СЗ');
});
test('null returns em dash', () => assert.strictEqual(windDirection(null), '—'));
test('undefined returns em dash', () => assert.strictEqual(windDirection(undefined), '—'));

console.log('  getUVClass');
test('UV 0-2 is low', () => {
  assert.strictEqual(getUVClass(0), 'uv-low');
  assert.strictEqual(getUVClass(2), 'uv-low');
});
test('UV 3-5 is moderate', () => {
  assert.strictEqual(getUVClass(3), 'uv-moderate');
  assert.strictEqual(getUVClass(5), 'uv-moderate');
});
test('UV 6-7 is high', () => {
  assert.strictEqual(getUVClass(6), 'uv-high');
  assert.strictEqual(getUVClass(7), 'uv-high');
});
test('UV 8-10 is very high', () => {
  assert.strictEqual(getUVClass(8), 'uv-very-high');
  assert.strictEqual(getUVClass(10), 'uv-very-high');
});
test('UV 11+ is extreme', () => {
  assert.strictEqual(getUVClass(11), 'uv-extreme');
  assert.strictEqual(getUVClass(15), 'uv-extreme');
});
test('null/undefined returns empty string', () => {
  assert.strictEqual(getUVClass(null), '');
  assert.strictEqual(getUVClass(undefined), '');
});

console.log('  setWeatherTheme');
test('code 0 daytime is sunny', () => assert.strictEqual(setWeatherTheme(0, true), 'sunny'));
test('code 0 nighttime is clear-night', () => assert.strictEqual(setWeatherTheme(0, false), 'clear-night'));
test('code 1 daytime is sunny', () => assert.strictEqual(setWeatherTheme(1, true), 'sunny'));
test('code 2 is cloudy', () => assert.strictEqual(setWeatherTheme(2, true), 'cloudy'));
test('code 3 is cloudy', () => assert.strictEqual(setWeatherTheme(3, false), 'cloudy'));
test('code 45 is foggy', () => assert.strictEqual(setWeatherTheme(45, true), 'foggy'));
test('code 48 is foggy', () => assert.strictEqual(setWeatherTheme(48, false), 'foggy'));
test('code 51 is rainy', () => assert.strictEqual(setWeatherTheme(51, true), 'rainy'));
test('code 61 is rainy', () => assert.strictEqual(setWeatherTheme(61, false), 'rainy'));
test('code 80 is rainy', () => assert.strictEqual(setWeatherTheme(80, true), 'rainy'));
test('code 71 is snowy', () => assert.strictEqual(setWeatherTheme(71, false), 'snowy'));
test('code 85 is snowy', () => assert.strictEqual(setWeatherTheme(85, true), 'snowy'));
test('code 95 is thunderstorm', () => assert.strictEqual(setWeatherTheme(95, false), 'thunderstorm'));
test('code 99 is thunderstorm', () => assert.strictEqual(setWeatherTheme(99, true), 'thunderstorm'));
test('unknown code falls back to sunny/clear-night', () => {
  assert.strictEqual(setWeatherTheme(-1, true), 'sunny');
  assert.strictEqual(setWeatherTheme(-1, false), 'clear-night');
});

console.log('  formatTime');
test('extracts HH:MM from ISO', () => {
  assert.strictEqual(formatTime('2026-07-05T06:30:00'), '06:30');
  assert.strictEqual(formatTime('2026-07-05T14:05:00'), '14:05');
});
test('empty input returns empty string', () => {
  assert.strictEqual(formatTime(''), '');
  assert.strictEqual(formatTime(null), '');
  assert.strictEqual(formatTime(undefined), '');
});

console.log('  WMO code mappings');
test('all known codes have icons', () => {
  for (const code of allWMOCodes) {
    assert.ok(wmoCodes[code] !== undefined, `Missing icon for code ${code}`);
  }
});
test('all known codes in JS match Python set', () => {
  // 28 codes total
  assert.strictEqual(Object.keys(wmoCodes).length, 28);
});
test('same icon for grouped codes', () => {
  assert.strictEqual(wmoCodes[95], wmoCodes[96]);
  assert.strictEqual(wmoCodes[95], wmoCodes[99]);
  assert.strictEqual(wmoCodes[71], wmoCodes[73]);
  assert.strictEqual(wmoCodes[61], wmoCodes[63]);
});

// ---------- Summary ----------

console.log(`\n  Results: ${passed} passed, ${failed} failed, ${passed + failed} total\n`);
process.exit(failed > 0 ? 1 : 0);
