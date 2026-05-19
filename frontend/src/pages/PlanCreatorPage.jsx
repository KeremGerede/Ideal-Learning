// src/pages/PlanCreatorPage.jsx

import { useState } from "react";
import { generatePlan } from "../api/apiClient";

function PlanCreatorPage({ onViewCreatedPlan }) {
    /**
     * Yeni öğrenme planı oluşturma sayfası.
     *
     * Bu sayfa Streamlit'teki plan oluşturma formunun React karşılığıdır.
     * Kullanıcıdan alınan bilgiler FastAPI backend'e gönderilir.
     */

    const [formData, setFormData] = useState({
        topic: "",
        level: "Başlangıç",
        goal: "",
        weekly_hours: 5,
        duration_weeks: 4,
        learning_preference: "Uygulamalı proje ağırlıklı",
    });

    const [createdPlan, setCreatedPlan] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errorMessage, setErrorMessage] = useState("");

    function handleChange(event) {
        /**
         * Form input değerlerini tek merkezden günceller.
         * number input'lardan gelen değerleri sayıya çeviriyoruz.
         */

        const { name, value } = event.target;

        const numericFields = ["weekly_hours", "duration_weeks"];

        setFormData((previousData) => ({
            ...previousData,
            [name]: numericFields.includes(name) ? Number(value) : value,
        }));
    }

    async function handleSubmit(event) {
        /**
         * Form submit edildiğinde backend'e plan oluşturma isteği gönderir.
         */

        event.preventDefault();

        setCreatedPlan(null);
        setErrorMessage("");

        if (!formData.topic.trim()) {
            setErrorMessage("Öğrenmek istediğin konu boş olamaz.");
            return;
        }

        if (!formData.goal.trim()) {
            setErrorMessage("Öğrenme hedefi boş olamaz.");
            return;
        }

        try {
            setIsSubmitting(true);

            const plan = await generatePlan(formData);

            setCreatedPlan(plan);
        } catch (error) {
            // error.message is the already-parsed detail string from apiClient.js
            setErrorMessage(
                error.message || "Plan oluşturulurken bir hata oluştu. Lütfen tekrar deneyin."
            );
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <div className="space-y-8">
            {/* Sayfa başlığı */}
            <section>
                <div className="inline-flex rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-sm text-indigo-200">
                    Yeni öğrenme planı
                </div>

                <h2 className="mt-5 max-w-3xl text-4xl font-bold tracking-tight text-slate-50 md:text-5xl">
                    Hedefine göre kişiselleştirilmiş bir öğrenme planı oluştur.
                </h2>

                <p className="mt-4 max-w-2xl text-slate-400">
                    Konunu, seviyeni, hedefini ve haftalık çalışma süreni gir. Sistem sana AI destekli haftalık öğrenme planı oluştursun.
                </p>
            </section>

            {/* Form kartı */}
            <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl shadow-slate-950/30">
                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Konu */}
                    <div>
                        <label className="text-sm font-semibold text-slate-200">
                            Öğrenmek istediğin konu
                        </label>

                        <input
                            type="text"
                            name="topic"
                            value={formData.topic}
                            onChange={handleChange}
                            placeholder="Örn: Python, React, Jenkins, Kubernetes"
                            className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-indigo-500"
                        />
                    </div>

                    {/* Hedef */}
                    <div>
                        <label className="text-sm font-semibold text-slate-200">
                            Öğrenme hedefin
                        </label>

                        <textarea
                            name="goal"
                            value={formData.goal}
                            onChange={handleChange}
                            placeholder="Örn: Stajımda CI/CD süreçlerini anlayıp basit pipeline yazabilmek istiyorum."
                            rows="4"
                            className="mt-2 w-full resize-none rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-indigo-500"
                        />
                    </div>

                    {/* Seviye ve tercih */}
                    <div className="grid gap-5 md:grid-cols-2">
                        <div>
                            <label className="text-sm font-semibold text-slate-200">
                                Mevcut seviyen
                            </label>

                            <select
                                name="level"
                                value={formData.level}
                                onChange={handleChange}
                                className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-500"
                            >
                                <option value="Başlangıç">Başlangıç</option>
                                <option value="Orta">Orta</option>
                                <option value="İleri">İleri</option>
                            </select>
                        </div>

                        <div>
                            <label className="text-sm font-semibold text-slate-200">
                                Öğrenme tercihin
                            </label>

                            <select
                                name="learning_preference"
                                value={formData.learning_preference}
                                onChange={handleChange}
                                className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-500"
                            >
                                <option value="Karışık">Karışık</option>
                                <option value="Video ağırlıklı">Video ağırlıklı</option>
                                <option value="Yazılı kaynak ağırlıklı">Yazılı kaynak ağırlıklı</option>
                                <option value="Uygulamalı proje ağırlıklı">Uygulamalı proje ağırlıklı</option>
                                <option value="Quiz ve tekrar ağırlıklı">Quiz ve tekrar ağırlıklı</option>
                            </select>
                        </div>
                    </div>

                    {/* Süre ayarları */}
                    <div className="grid gap-5 md:grid-cols-2">
                        <div>
                            <label className="text-sm font-semibold text-slate-200">
                                Haftalık kaç saat ayırabilirsin?
                            </label>

                            <input
                                type="number"
                                name="weekly_hours"
                                value={formData.weekly_hours}
                                onChange={handleChange}
                                min="1"
                                max="40"
                                className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-500"
                            />
                        </div>

                        <div>
                            <label className="text-sm font-semibold text-slate-200">
                                Kaç haftalık plan istiyorsun?
                            </label>

                            <input
                                type="number"
                                name="duration_weeks"
                                value={formData.duration_weeks}
                                onChange={handleChange}
                                min="1"
                                max="24"
                                className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-500"
                            />
                        </div>
                    </div>

                    {/* Hata mesajı */}
                    {errorMessage && (
                        <div className="rounded-2xl border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                            {errorMessage}
                        </div>
                    )}

                    {/* Submit */}
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="w-full rounded-2xl bg-indigo-500 px-5 py-4 text-sm font-bold text-white shadow-lg shadow-indigo-500/25 transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSubmitting ? "Plan oluşturuluyor..." : "AI ile Plan Oluştur"}
                    </button>
                </form>
            </section>

            {/* Başarılı sonuç kartı */}
            {createdPlan && (
                <section className="rounded-3xl border border-emerald-500/20 bg-emerald-500/10 p-6">
                    <p className="text-sm font-semibold text-emerald-200">
                        Plan başarıyla oluşturuldu.
                    </p>

                    <h3 className="mt-3 text-2xl font-bold text-slate-50">
                        {createdPlan.topic} - {createdPlan.level}
                    </h3>

                    <p className="mt-3 text-slate-300">
                        {createdPlan.summary || "Plan özeti bulunamadı."}
                    </p>

                    <div className="mt-5 grid gap-4 md:grid-cols-3">
                        <div className="rounded-2xl bg-slate-950/50 p-4">
                            <p className="text-xs text-slate-500">Süre</p>
                            <p className="mt-1 text-lg font-bold text-slate-100">
                                {createdPlan.duration_weeks} hafta
                            </p>
                        </div>

                        <div className="rounded-2xl bg-slate-950/50 p-4">
                            <p className="text-xs text-slate-500">Haftalık Saat</p>
                            <p className="mt-1 text-lg font-bold text-slate-100">
                                {createdPlan.weekly_hours} saat
                            </p>
                        </div>

                        <div className="rounded-2xl bg-slate-950/50 p-4">
                            <p className="text-xs text-slate-500">Hafta Sayısı</p>
                            <p className="mt-1 text-lg font-bold text-slate-100">
                                {createdPlan.weeks?.length || 0}
                            </p>
                        </div>
                    </div>

                    {/* Detay sayfasına yönlendirme butonu */}
                    {/* Oluşturulan planın detay sayfasına geçiş sağlar. */}
                    <button
                        type="button"
                        onClick={() => onViewCreatedPlan(createdPlan.id)}
                        className="mt-6 rounded-2xl bg-emerald-500 px-5 py-3 text-sm font-bold text-slate-950 transition hover:bg-emerald-400"
                    >
                        Plan Detaylarına Git
                    </button>
                </section>
            )}
        </div>
    );
}

export default PlanCreatorPage;