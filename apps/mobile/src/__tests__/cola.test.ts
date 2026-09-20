import { useCola } from '@/lib/cola';
import { useSesion } from '@/stores/sesion';

jest.mock('@/lib/almacen', () => {
  const memoria = new Map<string, unknown>();
  return {
    leer: async (k: string) => memoria.get(k) ?? null,
    guardar: async (k: string, v: unknown) => void memoria.set(k, v),
    borrar: async (k: string) => void memoria.delete(k),
    vaciar: async () => memoria.clear(),
  };
});

const base = { metodo: 'POST' as const, ruta: '/x', cuerpo: {} };

describe('cola de mutaciones offline', () => {
  beforeEach(async () => {
    useSesion.setState({ acceso: 'token' });
    useCola.setState({ pendientes: [], procesando: false });
    jest.restoreAllMocks();
  });

  it('se frena en el primer fallo de red y conserva el orden', async () => {
    await useCola.getState().encolar({ ...base, id: 'a', descripcion: 'a' });
    await useCola.getState().encolar({ ...base, id: 'b', descripcion: 'b' });
    const fetchMock = jest.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('sin red'));
    await useCola.getState().procesar();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(useCola.getState().pendientes.map((m) => m.id)).toEqual(['a', 'b']);
  });

  it('un rechazo del servidor no se reintenta: queda marcado con el mensaje', async () => {
    await useCola.getState().encolar({ ...base, id: 'a', descripcion: 'a' });
    await useCola.getState().encolar({ ...base, id: 'b', descripcion: 'b' });
    jest
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({ mensaje: 'El bruto no supera la tara' }),
      } as Response)
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) } as Response);
    const confirmadas: string[] = [];
    await useCola.getState().procesar((m) => confirmadas.push(m.id));
    const [a] = useCola.getState().pendientes;
    expect(a.id).toBe('a');
    expect(a.error).toBe('El bruto no supera la tara');
    expect(confirmadas).toEqual(['b']);
    await useCola.getState().descartar('a');
    expect(useCola.getState().pendientes).toEqual([]);
  });
});
