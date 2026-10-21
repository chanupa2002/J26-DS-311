import { createContext, useContext } from "react"

const THEME_KEY = "swss-theme"

export const ThemeContext = createContext(null)

export function getInitialTheme() {
  const savedTheme = window.localStorage.getItem(THEME_KEY)
  if (savedTheme === "light" || savedTheme === "dark") return savedTheme
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light"
}

export function applyTheme(theme) {
  document.documentElement.classList.toggle("dark", theme === "dark")
  document.documentElement.style.colorScheme = theme
}

export function saveTheme(theme) {
  window.localStorage.setItem(THEME_KEY, theme)
}

export function useTheme() {
  const value = useContext(ThemeContext)
  if (!value) throw new Error("useTheme must be used inside AppProviders")
  return value
}
