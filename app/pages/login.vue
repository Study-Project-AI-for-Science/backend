<script setup lang="ts">
const form = reactive({ email: '', password: '' })
const loading = ref(false)
const session = useUserSession()

async function submit() {
  loading.value = true
  try {
    await $fetch('/api/login', { method: 'POST', body: form })
    await session.fetch()
    await navigateTo('/')
  } catch (err) {
    console.error(err)
    alert('Login failed')
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
      </form>
    </DPageEmpty>
  </DPage>
</template>
