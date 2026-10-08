// Extrae los datos del viaje embebidos en el index.html de PIC Campo original (Paramillos 2026)
// y los imprime como JSON. Uso: node extraer_datos_pic.js index_original.html > datos.json
const fs = require('fs'), vm = require('vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const corte = (desde, hasta) => {
  const i = html.indexOf(desde), j = html.indexOf(hasta, i);
  if (i < 0 || j < 0) throw new Error('No encontré ' + desde);
  return html.slice(i, j);
};
const codigo = [
  corte('const VIAJE = {', '/* ============ Paradas'),
  corte('const PRESETS = {', 'const Mapa = {'),
  corte('const TELE = {', '// los botones flotantes'),
].join('\n') + '\n;({ VIAJE, PARADAS_BASE, PLAN, UNIDADES, GUIA, PRESETS, TELE: Object.fromEntries(Object.entries(TELE).filter(([k, v]) => typeof v !== "function")), TELE_LEY, TELE_GRUPOS })';
const datos = vm.runInNewContext(codigo, {});
process.stdout.write(JSON.stringify(datos, null, 1));
