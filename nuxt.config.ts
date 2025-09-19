import tailwindcss from "@tailwindcss/vite"

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "latest",
  devtools: { enabled: false },
  css: ["@/assets/main.css"],
  future: { compatibilityVersion: 4 },
  vite: { plugins: [tailwindcss()] },

  runtimeConfig: {
    s3AccessKeyId: process.env.NUXT_S3_ACCESS_KEY_ID,
    s3SecretAccessKey: process.env.NUXT_S3_SECRET_ACCESS_KEY,
    s3Endpoint: process.env.NUXT_S3_ENDPOINT,
    s3Bucket: process.env.NUXT_S3_BUCKET,
    s3Region: process.env.NUXT_S3_REGION,

    appUrl: "http://localhost:3000",
  },

  app: {
    head: {
      title: "Study Project: AI for Science",
    },
  },

  modules: ["nuxt-auth-utils", "@vueuse/nuxt"],
})
