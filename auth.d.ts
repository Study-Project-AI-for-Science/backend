declare module "#auth-utils" {
  interface User {
    id: number
    name: string
  }

  interface UserSession {
    // Add your own fields
  }

  interface SecureSessionData {
    userId: number
    sessionToken: string
  }
}

export {}
