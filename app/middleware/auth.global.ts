const publicRoutes = ["/login", "/register", "/logout"]

export default defineNuxtRouteMiddleware(async (to) => {
  // Skip authentication in development mode
  if (process.dev) {
    return
  }

  const session = useUserSession()

  if (!session.ready.value) {
    await session.fetch()
  }

  if (!session.loggedIn.value && !publicRoutes.includes(to.path)) {
    return navigateTo("/login")
  }

  if (session.loggedIn.value && ["/login", "/register"].includes(to.path)) {
    return navigateTo("/")
  }
})
