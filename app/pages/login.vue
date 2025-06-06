<script setup lang="ts">
const form = reactive({ email: '', password: '' })
const loading = ref(false)
const session = useUserSession()
const errorMessage = ref('')

async function submit() {
  loading.value = true
  try {
    await $fetch('/api/login', { method: 'POST', body: form })
    await session.fetch()
    await navigateTo('/')
  } catch (err) {
    console.error('Login error:', err)

    // More user-friendly error messages
    const error = err as { status?: number }
    if (error.status === 401) {
      errorMessage.value = 'Invalid credentials'
    } else if (error.status === 429) {
      errorMessage.value = 'Too many attempts, try again later'
    } else {
      errorMessage.value = 'Login failed. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <DPage>
    <DPageEmpty>
      <form @submit.prevent="submit" class="flex w-full max-w-xs flex-col gap-2">
        <h1 class="mb-2 text-xl font-semibold">Login</h1>
        <DLabel>Email</DLabel>
        <DInput v-model="form.email" type="email" />
        <DLabel>Password</DLabel>
        <DInput v-model="form.password" type="password" />
        <DButton type="submit" :loading="loading" textCenter>Login</DButton>
        <NuxtLink class="text-blue-600" to="/register">Create account</NuxtLink>
        <p v-if="errorMessage" class="mt-2 text-red-600">{{ errorMessage }}</p>
      </form>
    </DPageEmpty>
  </DPage>
</template>
