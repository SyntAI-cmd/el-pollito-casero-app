/**
 * Tokens del sistema de diseño. Este archivo es JS puro porque lo lee tailwind.config.js
 * (Node) y también la app (RN) donde un className no alcanza: mapas, sombras, iconos.
 */
const colors = {
  primary: '#F74603',
  'primary-press': '#DD0200',
  charcoal: '#1A0706',
  cherry: '#55100D',
  background: '#F4F2F1',
  surface: '#F9F9F9',
  'surface-white': '#FFFFFF',
  border: '#E5E0DE',
  'on-surface': '#1B1C1C',
  'on-surface-v': '#5C4038',
  success: '#1E8E5A',
  pending: '#646464',
  danger: '#DD0200',
};

const sombras = {
  card: { shadowColor: '#1A0706', shadowOpacity: 0.06, shadowRadius: 16, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  hero: { shadowColor: '#1A0706', shadowOpacity: 0.12, shadowRadius: 24, shadowOffset: { width: 0, height: 8 }, elevation: 6 },
  nav: { shadowColor: '#1A0706', shadowOpacity: 0.28, shadowRadius: 32, shadowOffset: { width: 0, height: 12 }, elevation: 12 },
  fab: { shadowColor: '#F74603', shadowOpacity: 0.38, shadowRadius: 20, shadowOffset: { width: 0, height: 8 }, elevation: 8 },
};

/** Área táctil mínima: el repartidor opera con guantes o manos mojadas. */
const TOQUE_MINIMO = 48;

module.exports = { tokens: { colors, sombras, TOQUE_MINIMO } };
