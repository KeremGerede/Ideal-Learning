// src/components/PlanCard.jsx

function PlanCard({ plan, onDelete, onViewDetail }) {
    /**
     * Kayıtlı öğrenme planını kart olarak gösterir.
     *
     * Detayı Gör:
     * - Seçilen plan ID'sini üst component'e gönderir.
     *
     * Sil:
     * - Planı backend üzerinden siler.
     */

    const totalWeeks = plan.weeks?.length || 0;

    return (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl shadow-slate-950/30">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                <div>
                    <p className="text-sm font-semibold text-indigo-300">
                        {plan.level}
                    </p>

                    <h3 className="mt-2 text-2xl font-bold text-slate-50">
                        {plan.topic}
                    </h3>

                    <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">
                        {plan.summary || plan.goal}
                    </p>
                </div>

                <div className="flex gap-3">
                    <button
                        type="button"
                        onClick={() => onViewDetail(plan.id)}
                        className="rounded-2xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 transition hover:border-indigo-500 hover:text-white"
                    >
                        Detayı Gör
                    </button>

                    <button
                        type="button"
                        onClick={() => onDelete(plan.id)}
                        className="rounded-2xl border border-red-900/70 bg-red-950/30 px-4 py-2 text-sm font-semibold text-red-200 transition hover:bg-red-900/40"
                    >
                        Sil
                    </button>
                </div>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-4">
                <div className="rounded-2xl bg-slate-950/60 p-4">
                    <p className="text-xs text-slate-500">Süre</p>
                    <p className="mt-1 text-lg font-bold text-slate-100">
                        {plan.duration_weeks} hafta
                    </p>
                </div>

                <div className="rounded-2xl bg-slate-950/60 p-4">
                    <p className="text-xs text-slate-500">Haftalık Saat</p>
                    <p className="mt-1 text-lg font-bold text-slate-100">
                        {plan.weekly_hours} saat
                    </p>
                </div>

                <div className="rounded-2xl bg-slate-950/60 p-4">
                    <p className="text-xs text-slate-500">Hafta Sayısı</p>
                    <p className="mt-1 text-lg font-bold text-slate-100">
                        {totalWeeks}
                    </p>
                </div>

                <div className="rounded-2xl bg-slate-950/60 p-4">
                    <p className="text-xs text-slate-500">Tercih</p>
                    <p className="mt-1 text-sm font-bold text-slate-100">
                        {plan.learning_preference || "Belirtilmedi"}
                    </p>
                </div>
            </div>
        </div>
    );
}

export default PlanCard;