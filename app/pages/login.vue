<script setup lang="ts">
const email = ref("")
const password = ref("")
const loading = ref(false)
const session = useUserSession()
const errorMessage = ref("")

async function signIn() {
  loading.value = true
  try {
    await $fetch("/api/login", { method: "POST", body: form })
    await session.fetch()
    await navigateTo("/")
  } catch (err) {
    console.error("Login error:", err)

    // More user-friendly error messages
    const error = err as { status?: number }
    if (error.status === 401) {
      errorMessage.value = "Invalid credentials"
    } else if (error.status === 429) {
      errorMessage.value = "Too many attempts, try again later"
    } else {
      errorMessage.value = "Login failed. Please try again."
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-neutral-100 px-8 pt-24">
    <div class="mx-auto max-w-sm rounded-lg border border-neutral-50 bg-white p-8 shadow">
      <h1 class="mb-4 text-center text-2xl font-semibold text-neutral-900">Sign In</h1>

      <form @submit.prevent="signIn" class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <d-label for="email">Email</d-label>
          <d-input
            v-model="email"
            type="email"
            id="email"
            name="email"
            required
            placeholder="Your email address"
          />
        </div>
        <div class="flex flex-col gap-1">
          <d-label for="password">Password</d-label>
          <d-input
            v-model="password"
            type="password"
            id="password"
            name="password"
            required
            placeholder="Your password"
          />
        </div>
        <d-button :loading type="submit" class="items-center justify-center bg-black text-white">
          Sign In
        </d-button>
        <div
          v-if="errorMessage"
          class="mb-2 rounded-md bg-red-100 px-4 py-2 text-center text-sm text-red-600"
        >
          {{ errorMessage }}
        </div>
        <p class="text-center text-sm text-neutral-500">
          Forgot your password?
          <NuxtLink to="/forgot-password" class="hover:underline">Reset password</NuxtLink>
        </p>
      </form>
    </div>
  </div>
</template>
