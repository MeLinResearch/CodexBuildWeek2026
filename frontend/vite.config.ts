import path from 'node:path';
import tailwindcss from '@tailwindcss/vite';
import { tanstackRouter } from '@tanstack/router-plugin/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [tanstackRouter({ target: 'react', autoCodeSplitting: true }), react(), tailwindcss()],
  build: {
    // The diff renderer emits syntax grammars as lazy chunks. Some individual
    // Shiki grammars exceed Vite's 500 kB default but are not startup payloads.
    chunkSizeWarningLimit: 800,
  },
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 9000,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:9001',
    },
  },
});
