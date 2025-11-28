"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Scale,
  Loader2,
  AlertCircle,
  Eye,
  EyeOff,
  FileSearch,
  AlertTriangle,
  ListChecks,
  Mic,
  CheckCircle2,
} from "lucide-react";
import { LanguageSelector } from "@/components/ui/language-selector";
import { authApi } from "@/lib/api";

export default function LoginPage() {
  const t = useTranslations("login");
  const router = useRouter();

  // Login form state
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Register form state
  const [registerName, setRegisterName] = useState("");
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [registerConfirmPassword, setRegisterConfirmPassword] = useState("");
  const [showRegisterPassword, setShowRegisterPassword] = useState(false);
  const [showRegisterConfirmPassword, setShowRegisterConfirmPassword] =
    useState(false);
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [registerLoading, setRegisterLoading] = useState(false);
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [registerSuccess, setRegisterSuccess] = useState(false);

  // Field-level validation errors
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const validateEmail = (email: string): string | null => {
    if (!email) return t("validation.emailRequired");
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) return t("validation.emailInvalid");
    return null;
  };

  const validatePassword = (password: string): string | null => {
    if (!password) return t("validation.passwordRequired");
    if (password.length < 8) return t("validation.passwordTooShort");
    return null;
  };

  const validateName = (name: string): string | null => {
    if (!name) return t("validation.nameRequired");
    if (name.length < 2) return t("validation.nameTooShort");
    return null;
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);
    setFieldErrors({});

    // Validate fields
    const errors: Record<string, string> = {};
    const emailError = validateEmail(loginEmail);
    const passwordError = validatePassword(loginPassword);

    if (emailError) errors.loginEmail = emailError;
    if (passwordError) errors.loginPassword = passwordError;

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setLoginLoading(true);

    try {
      await authApi.login(loginEmail, loginPassword);
      router.push("/dashboard");
    } catch (err) {
      setLoginError(
        err instanceof Error ? err.message : t("errors.invalidCredentials")
      );
    } finally {
      setLoginLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegisterError(null);
    setFieldErrors({});

    // Validate fields
    const errors: Record<string, string> = {};
    const nameError = validateName(registerName);
    const emailError = validateEmail(registerEmail);
    const passwordError = validatePassword(registerPassword);

    if (nameError) errors.registerName = nameError;
    if (emailError) errors.registerEmail = emailError;
    if (passwordError) errors.registerPassword = passwordError;
    if (registerPassword !== registerConfirmPassword) {
      errors.registerConfirmPassword = t("validation.passwordMismatch");
    }
    if (!acceptTerms) {
      errors.acceptTerms = t("validation.termsRequired");
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setRegisterLoading(true);

    try {
      // Register new user
      await authApi.register(registerName, registerEmail, registerPassword);
      setRegisterSuccess(true);

      // Auto-login after successful registration
      await authApi.login(registerEmail, registerPassword);

      // Redirect after success message
      setTimeout(() => {
        router.push("/dashboard");
      }, 1500);
    } catch (err) {
      setRegisterError(
        err instanceof Error ? err.message : t("errors.serverError")
      );
    } finally {
      setRegisterLoading(false);
    }
  };

  const features = [
    { icon: FileSearch, text: t("presentation.feature1") },
    { icon: AlertTriangle, text: t("presentation.feature2") },
    { icon: ListChecks, text: t("presentation.feature3") },
    { icon: Mic, text: t("presentation.feature4") },
  ];

  return (
    <div className="min-h-screen flex">
      {/* Left Panel - Presentation */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary text-primary-foreground flex-col justify-between p-8 relative overflow-hidden">
        {/* Background pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 left-0 w-full h-full">
            <svg
              className="w-full h-full"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
            >
              <defs>
                <pattern
                  id="grid"
                  width="10"
                  height="10"
                  patternUnits="userSpaceOnUse"
                >
                  <path
                    d="M 10 0 L 0 0 0 10"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="0.5"
                  />
                </pattern>
              </defs>
              <rect width="100" height="100" fill="url(#grid)" />
            </svg>
          </div>
        </div>

        {/* Content */}
        <div className="relative z-10">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <Scale className="h-10 w-10" />
            <span className="text-2xl font-bold">Notary</span>
          </div>
        </div>

        <div className="relative z-10 flex-1 flex flex-col justify-center max-w-lg">
          <h1 className="text-4xl font-bold mb-2">{t("presentation.title")}</h1>
          <h2 className="text-5xl font-bold mb-6">
            {t("presentation.subtitle")}
          </h2>
          <p className="text-lg opacity-90 mb-8">{t("presentation.description")}</p>

          {/* Features */}
          <div className="space-y-4">
            {features.map((feature, index) => (
              <div key={index} className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary-foreground/10">
                  <feature.icon className="h-5 w-5" />
                </div>
                <span className="text-lg">{feature.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="relative z-10 text-sm opacity-70">
          <p>&copy; 2024 Notary Assistant. Tous droits réservés.</p>
        </div>
      </div>

      {/* Right Panel - Form */}
      <div className="flex-1 flex flex-col bg-muted/30">
        {/* Top bar with language selector */}
        <div className="flex justify-end p-4">
          <LanguageSelector />
        </div>

        {/* Form container */}
        <div className="flex-1 flex items-center justify-center px-4 py-8">
          <div className="w-full max-w-md space-y-6">
            {/* Mobile Logo */}
            <div className="flex flex-col items-center space-y-2 lg:hidden">
              <Link href="/" className="flex items-center gap-2">
                <Scale className="h-10 w-10 text-primary" />
                <span className="text-2xl font-bold">Notary Assistant</span>
              </Link>
            </div>

            {/* Form Card */}
            <Card className="shadow-lg">
              <Tabs defaultValue="login" className="w-full">
                <CardHeader className="pb-0">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="login">{t("title")}</TabsTrigger>
                    <TabsTrigger value="register">
                      {t("registerForm.title")}
                    </TabsTrigger>
                  </TabsList>
                </CardHeader>

                {/* Login Tab */}
                <TabsContent value="login">
                  <CardHeader className="pt-4 pb-2">
                    <CardTitle className="text-2xl">{t("title")}</CardTitle>
                    <CardDescription>{t("subtitle")}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleLogin} className="space-y-4">
                      {/* Error Message */}
                      {loginError && (
                        <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
                          <AlertCircle className="h-4 w-4 shrink-0" />
                          {loginError}
                        </div>
                      )}

                      {/* Email */}
                      <div className="space-y-2">
                        <Label htmlFor="login-email">{t("email")}</Label>
                        <Input
                          id="login-email"
                          type="email"
                          placeholder={t("emailPlaceholder")}
                          value={loginEmail}
                          onChange={(e) => {
                            setLoginEmail(e.target.value);
                            if (fieldErrors.loginEmail) {
                              setFieldErrors((prev) => ({
                                ...prev,
                                loginEmail: "",
                              }));
                            }
                          }}
                          disabled={loginLoading}
                          autoComplete="email"
                          className={
                            fieldErrors.loginEmail ? "border-destructive" : ""
                          }
                        />
                        {fieldErrors.loginEmail && (
                          <p className="text-sm text-destructive flex items-center gap-1">
                            <AlertCircle className="h-3 w-3" />
                            {fieldErrors.loginEmail}
                          </p>
                        )}
                      </div>

                      {/* Password */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label htmlFor="login-password">{t("password")}</Label>
                          <Link
                            href="/forgot-password"
                            className="text-sm text-primary hover:underline"
                          >
                            {t("forgotPassword")}
                          </Link>
                        </div>
                        <div className="relative">
                          <Input
                            id="login-password"
                            type={showLoginPassword ? "text" : "password"}
                            placeholder={t("passwordPlaceholder")}
                            value={loginPassword}
                            onChange={(e) => {
                              setLoginPassword(e.target.value);
                              if (fieldErrors.loginPassword) {
                                setFieldErrors((prev) => ({
                                  ...prev,
                                  loginPassword: "",
                                }));
                              }
                            }}
                            disabled={loginLoading}
                            autoComplete="current-password"
                            className={`pr-10 ${
                              fieldErrors.loginPassword ? "border-destructive" : ""
                            }`}
                          />
                          <button
                            type="button"
                            onClick={() => setShowLoginPassword(!showLoginPassword)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                            title={
                              showLoginPassword
                                ? t("hidePassword")
                                : t("showPassword")
                            }
                          >
                            {showLoginPassword ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                        {fieldErrors.loginPassword && (
                          <p className="text-sm text-destructive flex items-center gap-1">
                            <AlertCircle className="h-3 w-3" />
                            {fieldErrors.loginPassword}
                          </p>
                        )}
                      </div>

                      {/* Submit Button */}
                      <Button
                        type="submit"
                        className="w-full"
                        disabled={loginLoading}
                      >
                        {loginLoading ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            {t("logging")}
                          </>
                        ) : (
                          t("submit")
                        )}
                      </Button>

                      {/* Divider */}
                      <div className="relative my-4">
                        <div className="absolute inset-0 flex items-center">
                          <div className="w-full border-t" />
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
                          <span className="bg-card px-2 text-muted-foreground">
                            {t("orContinueWith")}
                          </span>
                        </div>
                      </div>

                      {/* Google Sign In (Optional) */}
                      <Button
                        type="button"
                        variant="outline"
                        className="w-full"
                        disabled={loginLoading}
                      >
                        <svg className="h-4 w-4 mr-2" viewBox="0 0 24 24">
                          <path
                            fill="currentColor"
                            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                          />
                          <path
                            fill="currentColor"
                            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                          />
                          <path
                            fill="currentColor"
                            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                          />
                          <path
                            fill="currentColor"
                            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                          />
                        </svg>
                        {t("continueWithGoogle")}
                      </Button>
                    </form>
                  </CardContent>
                </TabsContent>

                {/* Register Tab */}
                <TabsContent value="register">
                  <CardHeader className="pt-4 pb-2">
                    <CardTitle className="text-2xl">
                      {t("registerForm.title")}
                    </CardTitle>
                    <CardDescription>
                      {t("registerForm.subtitle")}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleRegister} className="space-y-4">
                      {/* Success Message */}
                      {registerSuccess && (
                        <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                          <CheckCircle2 className="h-4 w-4 shrink-0" />
                          {t("registerForm.success")}
                        </div>
                      )}

                      {/* Error Message */}
                      {registerError && (
                        <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
                          <AlertCircle className="h-4 w-4 shrink-0" />
                          {registerError}
                        </div>
                      )}

                      {/* Full Name */}
                      <div className="space-y-2">
                        <Label htmlFor="register-name">
                          {t("registerForm.fullName")}
                        </Label>
                        <Input
                          id="register-name"
                          type="text"
                          placeholder={t("registerForm.fullNamePlaceholder")}
                          value={registerName}
                          onChange={(e) => {
                            setRegisterName(e.target.value);
                            if (fieldErrors.registerName) {
                              setFieldErrors((prev) => ({
                                ...prev,
                                registerName: "",
                              }));
                            }
                          }}
                          disabled={registerLoading || registerSuccess}
                          autoComplete="name"
                          className={
                            fieldErrors.registerName ? "border-destructive" : ""
                          }
                        />
                        {fieldErrors.registerName && (
                          <p className="text-sm text-destructive flex items-center gap-1">
                            <AlertCircle className="h-3 w-3" />
                            {fieldErrors.registerName}
                          </p>
                        )}
                      </div>

                      {/* Email */}
                      <div className="space-y-2">
                        <Label htmlFor="register-email">{t("email")}</Label>
                        <Input
                          id="register-email"
                          type="email"
                          placeholder={t("emailPlaceholder")}
                          value={registerEmail}
                          onChange={(e) => {
                            setRegisterEmail(e.target.value);
                            if (fieldErrors.registerEmail) {
                              setFieldErrors((prev) => ({
                                ...prev,
                                registerEmail: "",
                              }));
                            }
                          }}
                          disabled={registerLoading || registerSuccess}
                          autoComplete="email"
                          className={
                            fieldErrors.registerEmail ? "border-destructive" : ""
                          }
                        />
                        {fieldErrors.registerEmail && (
                          <p className="text-sm text-destructive flex items-center gap-1">
                            <AlertCircle className="h-3 w-3" />
                            {fieldErrors.registerEmail}
                          </p>
                        )}
                      </div>

                      {/* Password */}
                      <div className="space-y-2">
                        <Label htmlFor="register-password">{t("password")}</Label>
                        <div className="relative">
                          <Input
                            id="register-password"
                            type={showRegisterPassword ? "text" : "password"}
                            placeholder={t("passwordPlaceholder")}
                            value={registerPassword}
                            onChange={(e) => {
                              setRegisterPassword(e.target.value);
                              if (fieldErrors.registerPassword) {
                                setFieldErrors((prev) => ({
                                  ...prev,
                                  registerPassword: "",
                                }));
                              }
                            }}
                            disabled={registerLoading || registerSuccess}
                            autoComplete="new-password"
                            className={`pr-10 ${
                              fieldErrors.registerPassword
                                ? "border-destructive"
                                : ""
                            }`}
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowRegisterPassword(!showRegisterPassword)
                            }
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                            title={
                              showRegisterPassword
                                ? t("hidePassword")
                                : t("showPassword")
                            }
                          >
                            {showRegisterPassword ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                        {fieldErrors.registerPassword && (
                          <p className="text-sm text-destructive flex items-center gap-1">
                            <AlertCircle className="h-3 w-3" />
                            {fieldErrors.registerPassword}
                          </p>
                        )}
                      </div>

                      {/* Confirm Password */}
                      <div className="space-y-2">
                        <Label htmlFor="register-confirm-password">
                          {t("registerForm.confirmPassword")}
                        </Label>
                        <div className="relative">
                          <Input
                            id="register-confirm-password"
                            type={
                              showRegisterConfirmPassword ? "text" : "password"
                            }
                            placeholder={t(
                              "registerForm.confirmPasswordPlaceholder"
                            )}
                            value={registerConfirmPassword}
                            onChange={(e) => {
                              setRegisterConfirmPassword(e.target.value);
                              if (fieldErrors.registerConfirmPassword) {
                                setFieldErrors((prev) => ({
                                  ...prev,
                                  registerConfirmPassword: "",
                                }));
                              }
                            }}
                            disabled={registerLoading || registerSuccess}
                            autoComplete="new-password"
                            className={`pr-10 ${
                              fieldErrors.registerConfirmPassword
                                ? "border-destructive"
                                : ""
                            }`}
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowRegisterConfirmPassword(
                                !showRegisterConfirmPassword
                              )
                            }
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                            title={
                              showRegisterConfirmPassword
                                ? t("hidePassword")
                                : t("showPassword")
                            }
                          >
                            {showRegisterConfirmPassword ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                        {fieldErrors.registerConfirmPassword && (
                          <p className="text-sm text-destructive flex items-center gap-1">
                            <AlertCircle className="h-3 w-3" />
                            {fieldErrors.registerConfirmPassword}
                          </p>
                        )}
                      </div>

                      {/* Terms Checkbox */}
                      <div className="space-y-2">
                        <div className="flex items-start space-x-2">
                          <Checkbox
                            id="terms"
                            checked={acceptTerms}
                            onCheckedChange={(checked) => {
                              setAcceptTerms(checked as boolean);
                              if (fieldErrors.acceptTerms) {
                                setFieldErrors((prev) => ({
                                  ...prev,
                                  acceptTerms: "",
                                }));
                              }
                            }}
                            disabled={registerLoading || registerSuccess}
                            className={
                              fieldErrors.acceptTerms
                                ? "border-destructive"
                                : ""
                            }
                          />
                          <label
                            htmlFor="terms"
                            className="text-sm leading-tight cursor-pointer"
                          >
                            {t("registerForm.terms")}{" "}
                            <Link
                              href="/terms"
                              className="text-primary hover:underline"
                            >
                              {t("registerForm.termsLink")}
                            </Link>{" "}
                            {t("registerForm.and")}{" "}
                            <Link
                              href="/privacy"
                              className="text-primary hover:underline"
                            >
                              {t("registerForm.privacyLink")}
                            </Link>
                          </label>
                        </div>
                        {fieldErrors.acceptTerms && (
                          <p className="text-sm text-destructive flex items-center gap-1">
                            <AlertCircle className="h-3 w-3" />
                            {fieldErrors.acceptTerms}
                          </p>
                        )}
                      </div>

                      {/* Submit Button */}
                      <Button
                        type="submit"
                        className="w-full"
                        disabled={registerLoading || registerSuccess}
                      >
                        {registerLoading ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            {t("registerForm.creating")}
                          </>
                        ) : (
                          t("registerForm.submit")
                        )}
                      </Button>
                    </form>
                  </CardContent>
                </TabsContent>
              </Tabs>
            </Card>

            {/* Demo Credentials */}
            <div className="text-center text-xs text-muted-foreground border-t pt-4">
              <p className="font-medium mb-1">{t("demoCredentials")}:</p>
              <p>notaire@test.com / notaire123</p>
            </div>

            {/* Contact Link */}
            <p className="text-center text-sm text-muted-foreground">
              <Link href="/contact" className="text-primary hover:underline">
                {t("contactUs")}
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
