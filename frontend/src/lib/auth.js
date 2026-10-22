const SESSION_KEY = "j26-ds-311-authenticated"

export function login(username, password) {
  const accepted = username === "Admin" && password === "Admin@123"
  if (accepted) sessionStorage.setItem(SESSION_KEY, "true")
  return accepted
}

export function logout() {
  sessionStorage.removeItem(SESSION_KEY)
}

export function isLoggedIn() {
  return sessionStorage.getItem(SESSION_KEY) === "true"
}
