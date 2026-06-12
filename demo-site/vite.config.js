import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  root: ".",
  publicDir: "public",
  build: {
    outDir: "dist",
    rollupOptions: {
      input: {
        index: resolve(__dirname, "index.html"),
        login: resolve(__dirname, "login.html"),
        signup: resolve(__dirname, "signup.html"),
        article: resolve(__dirname, "article.html"),
        memoryGame: resolve(__dirname, "memory-game.html"),
        quiz: resolve(__dirname, "quiz.html"),
        survey: resolve(__dirname, "survey.html"),
        typingTest: resolve(__dirname, "typing-test.html"),
      },
    },
  },
  server: {
    port: 5173,
    open: true,
  },
});