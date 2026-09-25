import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// envDir points at the repo root so frontend and backend share one .env file.
// Only variables prefixed with VITE_ are exposed to the browser - never put secrets there.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  envDir: '..',
  server: { port: 5173 },
})
