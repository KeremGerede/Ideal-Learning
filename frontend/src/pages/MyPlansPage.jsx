// src/pages/MyPlansPage.jsx

import { useEffect, useState } from "react";
import { deletePlanById, getAllPlans } from "../api/apiClient";
import PlanCard from "../components/PlanCard";

function MyPlansPage({ onViewPlanDetail }) {
    /**
     * Kullanıcının oluşturduğu tüm öğrenme planlarını listeler.
     *
     * Şu an authentication olmadığı için backend'deki tüm planlar listelenir.
     * İleride kullanıcı girişi eklenirse bu sayfa sadece aktif kullanıcının planlarını gösterecek.
     */

    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [errorMessage, setErrorMessage] = useState("");
    const [successMessage, setSuccessMessage] = useState("");

    async function loadPlans() {
        /**
         * Backend'den kayıtlı planları çeker.
         */

        try {
            setLoading(true);
            setErrorMessage("");

            const plansData = await getAllPlans();
            setPlans(plansData);
        } catch (error) {
            setErrorMessage(error.message || "Planlar alınırken hata oluştu.");
        } finally {
            setLoading(false);
        }
    }

    async function handleDeletePlan(planId) {
        /**
         * Seçilen planı siler ve listeyi günceller.
         */

        const confirmed = window.confirm(
            "Bu öğrenme planını silmek istediğine emin misin?"
        );

        if (!confirmed) {
            return;
        }

        try {
            setErrorMessage("");
            setSuccessMessage("");

            await deletePlanById(planId);

            setSuccessMessage("Plan başarıyla silindi.");

            // Silme işleminden sonra listeyi yeniden yüklüyoruz.
            await loadPlans();
        } catch (error) {
            setErrorMessage(error.message || "Plan silinirken hata oluştu.");
        }
    }

    useEffect(() => {
        /**
         * Sayfa ilk açıldığında planları yüklüyoruz.
         */

        loadPlans();
    }, []);

    return (
        <div className="space-y-8">
            {/* Sayfa başlığı */}
            <section>
                <div className="inline-flex rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-sm text-indigo-200">
                    Kayıtlı öğrenme planları
                </div>

                <h2 className="mt-5 text-4xl font-bold tracking-tight text-slate-50 md:text-5xl">
                    Planlarım
                </h2>

                <p className="mt-4 max-w-2xl text-slate-400">
                    Daha önce oluşturduğun öğrenme planlarını buradan görüntüleyebilir ve yönetebilirsin.
                </p>
            </section>

            {/* Bilgilendirme mesajları */}
            {successMessage && (
                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm font-semibold text-emerald-200">
                    {successMessage}
                </div>
            )}

            {errorMessage && (
                <div className="rounded-2xl border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                    {errorMessage}
                </div>
            )}

            {/* Loading durumu */}
            {loading && (
                <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8">
                    <p className="text-slate-400">
                        Planlar yükleniyor...
                    </p>
                </div>
            )}

            {/* Boş liste durumu */}
            {!loading && plans.length === 0 && (
                <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8">
                    <h3 className="text-xl font-bold text-slate-100">
                        Henüz plan yok
                    </h3>

                    <p className="mt-3 text-slate-400">
                        Plan Oluştur sayfasından ilk öğrenme planını oluşturabilirsin.
                    </p>
                </div>
            )}

            {/* Plan listesi */}
            {!loading && plans.length > 0 && (
                <section className="space-y-5">
                    {plans.map((plan) => (
                        <PlanCard
                            key={plan.id}
                            plan={plan}
                            onDelete={handleDeletePlan}
                            onViewDetail={onViewPlanDetail}
                        />
                    ))}
                </section>
            )}
        </div>
    );
}

export default MyPlansPage;