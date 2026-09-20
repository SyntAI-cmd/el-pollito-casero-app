import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react-native';
import type { ReactElement } from 'react';

import { EstadoApi } from '@/components/EstadoApi';

function renderConQuery(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('EstadoApi', () => {
  afterEach(() => jest.restoreAllMocks());

  it('muestra la API conectada cuando /health responde', async () => {
    jest.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ estado: 'ok', entorno: 'test', version: '0.1.0' }),
    } as Response);
    renderConQuery(<EstadoApi />);
    await waitFor(() =>
      expect(screen.getByTestId('estado-api')).toHaveTextContent(/API conectada/),
      { timeout: 4000 },
    );
  });

  it('avisa sin conexión cuando la API falla', async () => {
    jest.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('red'));
    renderConQuery(<EstadoApi />);
    await waitFor(() =>
      expect(screen.getByTestId('estado-api')).toHaveTextContent(/Sin conexión/),
      { timeout: 4000 },
    );
  });
});
