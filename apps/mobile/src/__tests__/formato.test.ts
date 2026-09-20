import { fechaLarga, kilos, pesos } from '@/lib/formato';

describe('formato rioplatense', () => {
  it('pesos con punto de miles y centavos solo cuando hay', () => {
    expect(pesos('840500.00')).toBe('$ 840.500');
    expect(pesos('12.50')).toBe('$ 12,50');
    expect(pesos('-300.00')).toBe('-$ 300');
    expect(pesos(null)).toBe('—');
  });

  it('kilos con coma decimal y sin ceros de más', () => {
    expect(kilos('480.500')).toBe('480,5 kg');
    expect(kilos('60.000')).toBe('60 kg');
    expect(kilos('1420.125')).toBe('1.420,125 kg');
  });

  it('fecha larga en castellano', () => {
    expect(fechaLarga('2026-09-18')).toBe('Viernes 18 de septiembre');
  });
});
