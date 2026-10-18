import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/app/",
  plugins: [react()],
  server: {
    proxy: {
      "/auth": "http://127.0.0.1:8000",
      "/notes": "http://127.0.0.1:8000",
      "/diaries": "http://127.0.0.1:8000",
      "/trash": "http://127.0.0.1:8000",
      "/records": "http://127.0.0.1:8000",
    },
  },
});
