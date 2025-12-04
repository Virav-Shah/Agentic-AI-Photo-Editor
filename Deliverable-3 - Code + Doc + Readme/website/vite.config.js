import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import svgr from 'vite-plugin-svgr'
import fs from 'fs'

export default defineConfig({
  plugins: [react(), svgr()],
  server: {
    host: true, // Allow access from network
    host: true, // Allow access from network

  }
})
