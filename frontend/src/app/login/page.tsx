"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, Building2, Eye, EyeOff, Lock, Mail, User } from "lucide-react";

import Logo from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import Toast from "@/components/Toast";
import { getToken, login, register, resendOtp, verifyOtp } from "@/lib/api";

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center bg-background">
          <div className="h-5 w-5 rounded-full border-2 border-zinc-700 border-t-transparent animate-spin" />
        </div>
      }
    >
      <AuthPageContent />
    </Suspense>
  );
}

function AuthPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialMode = searchParams.get("mode");

  const [mode, setMode] = useState<"signin" | "signup" | "verify_otp">(
    initialMode === "signup" || initialMode === "register" ? "signup" : "signin"
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [otp, setOtp] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [otpError, setOtpError] = useState("");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  useEffect(() => {
    if (getToken()) {
      router.push("/sites");
    }
  }, [router]);

  const validateEmail = (val: string) => {
    setEmail(val);
    if (!val) {
      setEmailError("Email address is required");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    setEmailError(emailRegex.test(val) ? "" : "Please enter a valid email address");
  };

  const validatePassword = (val: string) => {
    setPassword(val);
    if (!val) {
      setPasswordError("Password is required");
      return;
    }

    setPasswordError(val.length < 6 ? "Password must be at least 6 characters" : "");
  };

  const validateOtp = (val: string) => {
    const digitsOnly = val.replace(/\D/g, "");
    setOtp(digitsOnly);
    if (!digitsOnly) {
      setOtpError("Verification code is required");
      return;
    }

    setOtpError(digitsOnly.length === 6 ? "" : "Enter a valid 6-digit code");
  };

  const resetErrors = () => {
    setEmailError("");
    setPasswordError("");
    setOtpError("");
  };

  const handleResendOtp = async () => {
    setResending(true);
    setToast(null);
    try {
      await resendOtp(email);
      setToast({ message: "Verification code resent.", type: "success" });
    } catch (err: unknown) {
      setToast({ message: getErrorMessage(err, "Failed to resend code."), type: "error" });
    } finally {
      setResending(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setToast(null);

    if (mode === "verify_otp") {
      if (!otp || otp.length !== 6) {
        setOtpError("Enter a valid 6-digit code");
        return;
      }

      setLoading(true);
      try {
        await verifyOtp(email, otp);
        setToast({ message: "Email verified. Redirecting...", type: "success" });
        setTimeout(() => {
          router.push("/sites");
        }, 800);
      } catch (err: unknown) {
        setToast({ message: getErrorMessage(err, "Invalid code."), type: "error" });
      } finally {
        setLoading(false);
      }
      return;
    }

    if (!email) {
      setEmailError("Email is required");
      return;
    }
    if (!password) {
      setPasswordError("Password is required");
      return;
    }
    if (emailError || passwordError) {
      return;
    }

    setLoading(true);
    try {
      if (mode === "signin") {
        await login(email, password);
        setToast({ message: "Authenticated. Redirecting...", type: "success" });
        setTimeout(() => {
          router.push("/sites");
        }, 800);
      } else {
        await register(email, password, fullName, companyName);
        setToast({ message: "Verification code sent to your email.", type: "success" });
        setMode("verify_otp");
        setOtp("");
        setOtpError("");
      }
    } catch (err: unknown) {
      const errorMessage = getErrorMessage(err, "Authentication error.");
      if (mode === "signin" && errorMessage === "Email verification required") {
        setMode("verify_otp");
        setOtp("");
        setOtpError("");
        setToast({
          message: "Your email is not verified yet. Enter the OTP we sent to continue.",
          type: "error",
        });
        return;
      }

      setToast({ message: errorMessage, type: "error" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6 relative">
      <div className="absolute top-6 right-6">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-sm animate-fade-in">
        <div className="mb-8 flex flex-col items-center text-center">
          <Logo className="h-9 w-9 mb-3" />
          <h1 className="text-lg font-semibold text-foreground">Luminary Analytics</h1>
          <p className="text-[10px] text-muted uppercase tracking-[0.2em] font-medium mt-1">
            Privacy-First Web Telemetry
          </p>
        </div>

        <div className="rounded-lg border border-card-border bg-card p-6">
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-foreground">
              {mode === "signin"
                ? "Welcome back"
                : mode === "signup"
                  ? "Create your account"
                  : "Verify your email"}
            </h2>
            <p className="text-xs text-muted mt-1">
              {mode === "signin"
                ? "Enter your credentials to continue."
                : mode === "signup"
                  ? "Get started with privacy-friendly analytics."
                  : `We sent a 6-digit code to ${email}.`}
            </p>
          </div>

          {mode !== "verify_otp" && (
            <div className="relative mb-5 flex items-center justify-center">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-card-border" />
              </div>
              <span className="relative bg-card px-3 text-[10px] uppercase tracking-wider font-medium text-muted">
                Continue with email
              </span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {mode === "verify_otp" ? (
              <div className="animate-fade-in">
                <label htmlFor="otp" className="block text-[10px] font-medium text-muted mb-1.5 uppercase tracking-wider">
                  Verification Code
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted">
                    <Lock className="h-3.5 w-3.5" />
                  </div>
                  <input
                    id="otp"
                    type="text"
                    maxLength={6}
                    value={otp}
                    onChange={(e) => validateOtp(e.target.value)}
                    className="w-full rounded-md border border-card-border bg-transparent pl-9 pr-4 py-2 text-sm text-foreground placeholder:text-zinc-600 focus:border-zinc-500 focus:outline-none font-mono tracking-[0.3em] text-center"
                    placeholder="000000"
                    aria-invalid={otpError ? "true" : "false"}
                  />
                </div>
                {otpError && <span className="text-[10px] text-danger mt-1 block">{otpError}</span>}
              </div>
            ) : (
              <>
                {mode === "signup" && (
                  <div className="grid grid-cols-2 gap-3 animate-fade-in">
                    <div>
                      <label htmlFor="fullName" className="block text-[10px] font-medium text-muted mb-1.5 uppercase tracking-wider">
                        Full Name
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted">
                          <User className="h-3.5 w-3.5" />
                        </div>
                        <input
                          id="fullName"
                          type="text"
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          className="w-full rounded-md border border-card-border bg-transparent pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-zinc-600 focus:border-zinc-500 focus:outline-none"
                          placeholder="Jane Doe"
                        />
                      </div>
                    </div>
                    <div>
                      <label htmlFor="companyName" className="block text-[10px] font-medium text-muted mb-1.5 uppercase tracking-wider">
                        Company
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted">
                          <Building2 className="h-3.5 w-3.5" />
                        </div>
                        <input
                          id="companyName"
                          type="text"
                          value={companyName}
                          onChange={(e) => setCompanyName(e.target.value)}
                          className="w-full rounded-md border border-card-border bg-transparent pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-zinc-600 focus:border-zinc-500 focus:outline-none"
                          placeholder="Acme Inc."
                        />
                      </div>
                    </div>
                  </div>
                )}

                <div>
                  <label htmlFor="email" className="block text-[10px] font-medium text-muted mb-1.5 uppercase tracking-wider">
                    Email Address
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted">
                      <Mail className="h-3.5 w-3.5" />
                    </div>
                    <input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => validateEmail(e.target.value)}
                      className={`w-full rounded-md border bg-transparent pl-9 pr-4 py-2 text-sm text-foreground placeholder:text-zinc-600 focus:outline-none ${
                        emailError
                          ? "border-danger/40 focus:border-danger"
                          : "border-card-border focus:border-zinc-500"
                      }`}
                      placeholder="you@domain.com"
                      aria-invalid={emailError ? "true" : "false"}
                    />
                  </div>
                  {emailError && <span className="text-[10px] text-danger mt-1 block">{emailError}</span>}
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label htmlFor="password" className="block text-[10px] font-medium text-muted uppercase tracking-wider">
                      Password
                    </label>
                    {mode === "signin" && (
                      <a
                        href="#forgot"
                        onClick={(e) => {
                          e.preventDefault();
                          setToast({ message: "Password reset not available in demo.", type: "error" });
                        }}
                        className="text-[10px] font-medium text-muted hover:text-foreground transition-colors"
                      >
                        Forgot?
                      </a>
                    )}
                  </div>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted">
                      <Lock className="h-3.5 w-3.5" />
                    </div>
                    <input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => validatePassword(e.target.value)}
                      className={`w-full rounded-md border bg-transparent pl-9 pr-9 py-2 text-sm text-foreground placeholder:text-zinc-600 focus:outline-none ${
                        passwordError
                          ? "border-danger/40 focus:border-danger"
                          : "border-card-border focus:border-zinc-500"
                      }`}
                      placeholder="********"
                      aria-invalid={passwordError ? "true" : "false"}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted hover:text-foreground transition-colors cursor-pointer"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                  {passwordError && <span className="text-[10px] text-danger mt-1 block">{passwordError}</span>}
                </div>
              </>
            )}

            <button
              type="submit"
              disabled={loading || (mode !== "verify_otp" && (!!emailError || !!passwordError))}
              className="w-full mt-2 rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:opacity-40 disabled:pointer-events-none transition-opacity flex items-center justify-center gap-1.5 cursor-pointer"
            >
              {loading ? (
                <div className="h-4 w-4 rounded-full border-2 border-background border-t-transparent animate-spin" />
              ) : (
                <>
                  {mode === "signin" ? "Sign In" : mode === "signup" ? "Create Account" : "Verify Code"}
                  <ArrowRight className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </form>

          {mode === "verify_otp" ? (
            <div className="mt-5 flex flex-col items-center gap-2 text-xs">
              <div className="text-muted">
                Didn&apos;t receive it?{" "}
                <button
                  type="button"
                  disabled={resending}
                  onClick={handleResendOtp}
                  className="text-foreground hover:underline font-medium bg-transparent border-none p-0 cursor-pointer disabled:opacity-50"
                >
                  {resending ? "Sending..." : "Resend"}
                </button>
              </div>
              <button
                type="button"
                onClick={() => {
                  setMode("signup");
                  setOtpError("");
                }}
                className="text-muted hover:text-foreground font-medium bg-transparent border-none p-0 cursor-pointer"
              >
                Back to sign up
              </button>
            </div>
          ) : (
            <p className="mt-5 text-center text-xs text-muted">
              {mode === "signin" ? "Don't have an account?" : "Already have an account?"}{" "}
              <button
                type="button"
                onClick={() => {
                  setMode(mode === "signin" ? "signup" : "signin");
                  resetErrors();
                }}
                className="text-foreground hover:underline font-medium bg-transparent border-none p-0 cursor-pointer"
              >
                {mode === "signin" ? "Sign up" : "Log in"}
              </button>
            </p>
          )}
        </div>

        {mode === "signin" && (
          <div className="mt-4 rounded-md border border-card-border bg-white/[0.02] px-4 py-2.5 text-center">
            <p className="text-[10px] text-muted">
              Demo: <span className="text-zinc-400 font-mono">demo@luminary.dev</span> /{" "}
              <span className="text-zinc-400 font-mono">demo1234</span>
            </p>
          </div>
        )}

        {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      </div>
    </div>
  );
}
