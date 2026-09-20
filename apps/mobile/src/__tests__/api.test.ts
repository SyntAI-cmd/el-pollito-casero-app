import { apiBaseUrl } from '@/lib/api';

describe('apiBaseUrl', () => {
  const original = process.env.EXPO_PUBLIC_API_URL;
  afterEach(() => {
    process.env.EXPO_PUBLIC_API_URL = original;
  });

  it('respeta EXPO_PUBLIC_API_URL y le saca la barra final', () => {
    process.env.EXPO_PUBLIC_API_URL = 'https://api.ejemplo.com/';
    expect(apiBaseUrl()).toBe('https://api.ejemplo.com');
  });

  it('sin variable cae a localhost:8000', () => {
    delete process.env.EXPO_PUBLIC_API_URL;
    expect(apiBaseUrl()).toBe('http://localhost:8000');
  });
});
