import { defineConfig } from 'vite';

const backend = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export default defineConfig({
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: { '/api': { target: backend, changeOrigin: true } },
  },
});
