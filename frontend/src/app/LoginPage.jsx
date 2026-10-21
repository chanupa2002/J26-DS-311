import { zodResolver } from "@hookform/resolvers/zod"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { Navigate, useLocation, useNavigate } from "react-router-dom"
import { z } from "zod"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { isLoggedIn, login } from "@/lib/auth"

const loginSchema = z.object({
  username: z.string().min(1, "Enter your username."),
  password: z.string().min(1, "Enter your password."),
})

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [loginError, setLoginError] = useState("")
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  })

  if (isLoggedIn()) return <Navigate to="/" replace />

  const submit = (values) => {
    setLoginError("")
    if (!login(values.username, values.password)) {
      setLoginError("Incorrect username or password.")
      return
    }
    navigate(location.state?.from?.pathname || "/", { replace: true })
  }

  return (
    <div className="flex min-h-svh items-center justify-center bg-muted/40 px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center space-y-4 pb-6 text-center">
          <div className="rounded-xl bg-white p-2 shadow-sm ring-1 ring-black/5">
            <img
              src="/logo.jpg"
              alt="SWSS logo"
              className="size-24 object-contain"
            />
          </div>
          <div className="space-y-1">
            <CardTitle className="text-2xl font-bold">SWSS</CardTitle>
            <p className="text-sm text-muted-foreground">
              Social Welfare Support System
            </p>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <form className="space-y-5" onSubmit={handleSubmit(submit)}>
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                autoComplete="username"
                {...register("username")}
              />
              {errors.username && (
                <p className="text-sm text-destructive">
                  {errors.username.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-sm text-destructive">
                  {errors.password.message}
                </p>
              )}
            </div>
            {loginError && (
              <p
                role="alert"
                className="rounded-md bg-destructive/10 p-3 text-sm text-destructive"
              >
                {loginError}
              </p>
            )}
            <Button className="w-full" type="submit" disabled={isSubmitting}>
              Sign in
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
