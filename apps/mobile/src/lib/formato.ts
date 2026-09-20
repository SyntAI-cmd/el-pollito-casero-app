/** Formatos rioplatenses: $ 840.500 · 1.420,5 kg · 24 cajones. Sin floats en cálculos: solo texto. */

function separarMiles(entero: string): string {
  return entero.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

/** "840500.00" → "$ 840.500" ; "12.50" → "$ 12,50". Los centavos se muestran solo si no son 0. */
export function pesos(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined || valor === '') return '—';
  const [entero, decimales = ''] = String(valor).replace('-', '').split('.');
  const negativo = String(valor).startsWith('-');
  const centavos = decimales.padEnd(2, '0').slice(0, 2);
  const cuerpo = separarMiles(entero) + (centavos === '00' ? '' : `,${centavos}`);
  return `${negativo ? '-' : ''}$ ${cuerpo}`;
}

/** "480.500" → "480,5 kg" ; "60.000" → "60 kg". */
export function kilos(valor: string | number | null | undefined, unidad = ' kg'): string {
  if (valor === null || valor === undefined || valor === '') return '—';
  const [entero, decimales = ''] = String(valor).split('.');
  const recortado = decimales.replace(/0+$/, '');
  return `${separarMiles(entero)}${recortado ? `,${recortado}` : ''}${unidad}`;
}

export function cajones(cantidad: number): string {
  return `${cantidad} ${cantidad === 1 ? 'cajón' : 'cajones'}`;
}

const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
const MESES = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
];

/** "2026-09-18" → "Viernes 18 de septiembre". */
export function fechaLarga(iso: string): string {
  const [a, m, d] = iso.split('-').map(Number);
  const fecha = new Date(a, m - 1, d);
  const dia = DIAS[fecha.getDay()];
  return `${dia.charAt(0).toUpperCase()}${dia.slice(1)} ${d} de ${MESES[m - 1]}`;
}

/** Fecha operativa local (la del celular) en ISO corto. */
export function hoyIso(): string {
  const ahora = new Date();
  const mes = String(ahora.getMonth() + 1).padStart(2, '0');
  const dia = String(ahora.getDate()).padStart(2, '0');
  return `${ahora.getFullYear()}-${mes}-${dia}`;
}

export function horaCorta(iso: string | null | undefined): string {
  if (!iso) return '—';
  const fecha = new Date(iso);
  return `${String(fecha.getHours()).padStart(2, '0')}:${String(fecha.getMinutes()).padStart(2, '0')}`;
}

export const ETIQUETA_ESTADO: Record<string, string> = {
  recibido: 'Cargado',
  preparando: 'Pesado',
  en_camino: 'En reparto',
  entregado: 'Entregado',
  cancelado: 'Cancelado',
};

export const ETIQUETA_TURNO: Record<string, string> = { manana: 'Mañana', tarde: 'Tarde' };
