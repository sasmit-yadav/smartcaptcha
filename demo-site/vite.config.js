import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  publicDir: 'public',
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        index: resolve(__dirname, 'index.html'),
        login: resolve(__dirname, 'login.html'),
        signup: resolve(__dirname, 'signup.html'),
        shop: resolve(__dirname, 'shop.html'),
        article: resolve(__dirname, 'article.html'),
        playground: resolve(__dirname, 'playground.html'),
      },
    },
  },
  server: {
    port: 5173,
    open: true,
  },
});
