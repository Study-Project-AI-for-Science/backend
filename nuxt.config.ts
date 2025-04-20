import tailwindcss from "@tailwindcss/vite"
import { resolve } from "path"

const rootDir = resolve(__dirname, "..") // Go up one level from backend

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-03-26",
  devtools: { enabled: false },
  css: ["@/assets/main.css"],

  future: {
    compatibilityVersion: 4,
  },

  vite: {
    plugins: [tailwindcss()],
    server: {
      watch: {
        ignored: [
          "**/.git/**", // Git internal files
          "**/node_modules/**", // node_modules inside backend
          "**/dist/**", // Build output
          `${rootDir}/volumes/**`, // Top-level volumes directory
          `${rootDir}/archive/**`, // Top-level archive directory
          // Add other potentially large/unnecessary directories if needed
          // `${rootDir}/modules/**`, // Python modules
        ],
      },
    },
  },

  modules: ["nuxt-auth-utils"],
})
