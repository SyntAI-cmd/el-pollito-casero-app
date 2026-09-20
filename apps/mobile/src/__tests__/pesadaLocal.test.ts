import { aGramos, deGramos, netoDe } from '@/lib/pesadaLocal';

describe('aritmética de la balanza en gramos enteros', () => {
  it('convierte texto con coma o punto y hasta 3 decimales', () => {
    expect(aGramos('21.7')).toBe(21700);
    expect(aGramos('21,7')).toBe(21700);
    expect(aGramos('0.005')).toBe(5);
    expect(aGramos('abc')).toBeNaN();
    expect(aGramos('1.2345')).toBeNaN();
  });

  it('resta la tara sin errores de coma flotante', () => {
    expect(netoDe('21.7', '1.700')).toBe(20000);
    expect(netoDe('0.1', '0.02')).toBe(80); // 0.1 - 0.02 en float daría 0.08000000000000002
    expect(deGramos(20000)).toBe('20.000');
  });
});
