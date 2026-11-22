import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/auth": "http://localhost:8000",
      "/stations": "http://localhost:8000",
      "/sessions": "http://localhost:8000",
      "/customers": "http://localhost:8000",
      "/pricing": "http://localhost:8000",
      "/reports": "http://localhost:8000",
      "/reservations": "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/ready": "http://localhost:8000",
    },
  },
})
