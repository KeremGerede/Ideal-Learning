// src/pages/LoginPage.jsx

import { useState } from "react";
import { useAuth } from "../context/AuthContext";

function LoginPage({ onSwitchToRegister }) {
    const { login } = useAuth();

    const [formData, setFormData] = useState({ username: "", password: "" });
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errorMessage, setErrorMessage] = useState("");

    function handleChange(event) {
        const { name, value } = event.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    }

    async function handleSubmit(event) {
        event.preventDefault();
        setErrorMessage("");

        if (!formData.username.trim() || !formData.password.trim()) {
            setErrorMessage("Kullanıcı adı ve şifre boş olamaz.");
            return;
        }

        try {
            setIsSubmitting(true);
            await login(formData.username, formData.password);
        } catch (error) {
            let message = "Giriş yapılamadı. Lütfen tekrar deneyin.";
            try {
                const parsed = JSON.parse(error.message);
                if (parsed.detail) message = parsed.detail;
            } catch {
                if (error.message) message = error.message;
            }
            setErrorMessage(message);
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
            <div className="w-full max-w-md">
                {/* Logo */}
                <div className="mb-8 text-center">
                    <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-indigo-500/20 text-4xl">
                        🎓
                    </div>
                    <h1 className="text-3xl font-bold text-slate-50">Smart Learning</h1>
                    <p className="mt-2 text-slate-400">AI Destekli Öğrenme Planlayıcı</p>
                </div>

                {/* Card */}
                <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 shadow-xl shadow-slate-950/50">
                    <h2 className="mb-6 text-xl font-bold text-slate-100">Giriş Yap</h2>

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label className="text-sm font-semibold text-slate-300">
                                Kullanıcı Adı
                            </label>
                            <input
                                type="text"
                                name="username"
                                value={formData.username}
                                onChange={handleChange}
                                placeholder="kullaniciadi"
                                autoComplete="username"
                                className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-indigo-500"
                            />
                        </div>

                        <div>
                            <label className="text-sm font-semibold text-slate-300">
                                Şifre
                            </label>
                            <input
                                type="password"
                                name="password"
                                value={formData.password}
                                onChange={handleChange}
                                placeholder="••••••••"
                                autoComplete="current-password"
                                className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-indigo-500"
                            />
                        </div>

                        {errorMessage && (
                            <div className="rounded-2xl border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                                {errorMessage}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="w-full rounded-2xl bg-indigo-500 px-5 py-4 text-sm font-bold text-white shadow-lg shadow-indigo-500/25 transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {isSubmitting ? "Giriş yapılıyor..." : "Giriş Yap"}
                        </button>
                    </form>

                    <p className="mt-6 text-center text-sm text-slate-400">
                        Hesabın yok mu?{" "}
                        <button
                            type="button"
                            onClick={onSwitchToRegister}
                            className="font-semibold text-indigo-400 transition hover:text-indigo-300"
                        >
                            Kayıt Ol
                        </button>
                    </p>
                </div>
            </div>
        </div>
    );
}

export default LoginPage;
