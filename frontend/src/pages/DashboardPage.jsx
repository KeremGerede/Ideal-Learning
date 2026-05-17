// src/pages/DashboardPage.jsx

import { useEffect, useState } from "react";
import {
    getHealthStatus,
    getStatsOverview,
    getLearningRecommendations,
} from "../api/apiClient";
import StatCard from "../components/StatCard";

function DashboardPage() {
    /**
     * Dashboard sayfası.
     *
     * Bu sayfada:
     * - Backend sağlık durumu
     * - Genel plan/görev istatistikleri
     * - Quiz istatistikleri
     * - Önceki planlara göre Gemini destekli öğrenme önerileri
     * gösterilir.
     */

    const [health, setHealth] = useState(null);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [errorMessage, setErrorMessage] = useState("");

    // Gemini destekli öneri sistemi için state alanları.
    const [recommendations, setRecommendations] = useState([]);
    const [recommendationPlanCount, setRecommendationPlanCount] = useState(0);
    const [recommendationsLoading, setRecommendationsLoading] = useState(false);
    const [recommendationsError, setRecommendationsError] = useState("");

    async function loadDashboardData() {
        /**
         * Backend health ve dashboard stats verilerini çeker.
         */

        try {
            setLoading(true);
            setErrorMessage("");

            const healthData = await getHealthStatus();
            const statsData = await getStatsOverview();

            setHealth(healthData);
            setStats(statsData);
        } catch (error) {
            setErrorMessage(error.message || "Dashboard verileri alınamadı.");
        } finally {
            setLoading(false);
        }
    }

    async function loadRecommendations() {
        /**
         * Kullanıcının önceki öğrenme planlarına göre önerilen yeni konuları getirir.
         *
         * Not:
         * - Öneri sistemi hata verirse dashboard tamamen bozulmasın diye
         *   hatayı sadece öneri alanında gösteriyoruz.
         */

        try {
            setRecommendationsLoading(true);
            setRecommendationsError("");

            const recommendationData = await getLearningRecommendations(6);

            setRecommendations(recommendationData.recommendations || []);
            setRecommendationPlanCount(recommendationData.based_on_plan_count || 0);
        } catch (error) {
            setRecommendations([]);
            setRecommendationPlanCount(0);
            setRecommendationsError(
                error.message || "Öğrenme önerileri alınamadı."
            );
        } finally {
            setRecommendationsLoading(false);
        }
    }

    useEffect(() => {
        /**
         * Sayfa ilk açıldığında dashboard verilerini ve öğrenme önerilerini yüklüyoruz.
         */

        loadDashboardData();
        loadRecommendations();
    }, []);

    if (loading) {
        return (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8">
                <p className="text-slate-400">Dashboard verileri yükleniyor...</p>
            </div>
        );
    }

    if (errorMessage) {
        return (
            <div className="rounded-3xl border border-red-900/60 bg-red-950/30 p-8">
                <h2 className="text-xl font-bold text-red-200">
                    Backend bağlantısı kurulamadı
                </h2>

                <p className="mt-3 text-sm text-red-200/80">{errorMessage}</p>

                <p className="mt-4 text-sm text-slate-400">
                    FastAPI backend’in çalıştığından emin ol:
                </p>

                <code className="mt-3 block rounded-2xl bg-slate-950 p-4 text-sm text-slate-200">
                    uvicorn app.main:app --reload
                </code>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Sayfa başlığı */}
            <section>
                <div className="inline-flex rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-sm text-indigo-200">
                    AI destekli kişisel öğrenme platformu
                </div>

                <h2 className="mt-5 max-w-3xl text-4xl font-bold tracking-tight text-slate-50 md:text-5xl">
                    Öğrenme planlarını, görev ilerlemesini ve quiz başarılarını tek
                    panelden takip et.
                </h2>

                <p className="mt-4 max-w-2xl text-slate-400">
                    Bu React arayüzü, FastAPI backend’e bağlanarak plan, görev, quiz ve
                    kişiselleştirilmiş öneri verilerini gösterir.
                </p>
            </section>

            {/* Backend durumu */}
            <section className="rounded-3xl border border-emerald-500/20 bg-emerald-500/10 p-5">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                        <p className="text-sm font-semibold text-emerald-200">
                            Backend Durumu
                        </p>

                        <p className="mt-1 text-sm text-emerald-100/80">
                            API çalışıyor. AI provider: {health?.ai_provider || "bilinmiyor"}
                        </p>
                    </div>

                    <span className="w-fit rounded-full bg-emerald-500 px-4 py-2 text-sm font-bold text-slate-950">
                        {health?.status || "unknown"}
                    </span>
                </div>
            </section>

            {/* Görev ve plan metrikleri */}
            <section>
                <h3 className="mb-4 text-xl font-bold text-slate-100">
                    Genel Durum
                </h3>

                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <StatCard
                        title="Toplam Plan"
                        value={stats?.total_plans ?? 0}
                        description="Oluşturulan öğrenme planı"
                        icon="📚"
                    />

                    <StatCard
                        title="Toplam Görev"
                        value={stats?.total_tasks ?? 0}
                        description="Tüm planlardaki görevler"
                        icon="✅"
                    />

                    <StatCard
                        title="Tamamlanan Görev"
                        value={stats?.completed_tasks ?? 0}
                        description="İşaretlenen görev sayısı"
                        icon="🎯"
                    />

                    <StatCard
                        title="Genel İlerleme"
                        value={`%${stats?.overall_progress_percentage ?? 0}`}
                        description="Tamamlanan görev oranı"
                        icon="📈"
                    />
                </div>
            </section>

            {/* Quiz metrikleri */}
            <section>
                <h3 className="mb-4 text-xl font-bold text-slate-100">
                    Quiz İstatistikleri
                </h3>

                <div className="grid gap-4 md:grid-cols-3">
                    <StatCard
                        title="Toplam Quiz"
                        value={stats?.total_quizzes ?? 0}
                        description="Kaydedilmiş quiz sonucu"
                        icon="🧪"
                    />

                    <StatCard
                        title="Ortalama Başarı"
                        value={`%${stats?.average_quiz_score ?? 0}`}
                        description="Tüm quizlerin ortalaması"
                        icon="⭐"
                    />

                    <StatCard
                        title="En Son Quiz Skoru"
                        value={
                            stats?.latest_quiz_score === null ||
                                stats?.latest_quiz_score === undefined
                                ? "Yok"
                                : `%${stats.latest_quiz_score}`
                        }
                        description="Son kaydedilen quiz"
                        icon="📝"
                    />
                </div>
            </section>

            {/* Gemini destekli öğrenme önerileri */}
            <section>
                <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                    <div>
                        <h3 className="text-2xl font-bold text-slate-100">
                            Bunları da öğrenmek isteyebilirsiniz
                        </h3>

                        <p className="mt-2 text-sm text-slate-500">
                            Önceki {recommendationPlanCount} öğrenme planına göre Gemini
                            tarafından önerildi.
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={loadRecommendations}
                        disabled={recommendationsLoading}
                        className="w-fit rounded-2xl border border-indigo-500/40 px-4 py-2 text-sm font-bold text-indigo-200 transition hover:bg-indigo-500 hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {recommendationsLoading ? "Yükleniyor..." : "Önerileri Yenile"}
                    </button>
                </div>

                {recommendationsError && (
                    <div className="rounded-2xl border border-red-900/60 bg-red-950/40 p-4">
                        <p className="text-sm text-red-200">{recommendationsError}</p>
                    </div>
                )}

                {!recommendationsError && recommendationsLoading && (
                    <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
                        <p className="text-sm text-slate-400">
                            Öğrenme önerileri hazırlanıyor...
                        </p>
                    </div>
                )}

                {!recommendationsError &&
                    !recommendationsLoading &&
                    recommendations.length === 0 && (
                        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
                            <p className="text-sm text-slate-400">
                                Henüz öneri oluşturmak için yeterli öğrenme geçmişi bulunamadı.
                            </p>
                        </div>
                    )}

                {!recommendationsError && recommendations.length > 0 && (
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                        {recommendations.map((recommendation) => (
                            <div
                                key={`${recommendation.topic}-${recommendation.suggested_level}`}
                                className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5 shadow-lg shadow-slate-950/20"
                            >
                                <div className="flex flex-wrap gap-2">
                                    <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-bold text-indigo-200">
                                        {recommendation.suggested_level}
                                    </span>

                                    <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-200">
                                        {recommendation.suggested_learning_preference || "Dengeli"}
                                    </span>
                                </div>

                                <h4 className="mt-4 text-xl font-bold text-slate-50">
                                    {recommendation.topic}
                                </h4>

                                <p className="mt-3 text-sm leading-6 text-slate-400">
                                    {recommendation.reason}
                                </p>

                                <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
                                    <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                        Önerilen hedef
                                    </p>

                                    <p className="mt-2 text-sm leading-6 text-slate-300">
                                        {recommendation.suggested_goal}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}

export default DashboardPage;