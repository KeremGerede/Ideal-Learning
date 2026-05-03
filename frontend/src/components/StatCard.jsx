// src/components/StatCard.jsx

function StatCard({ title, value, description, icon }) {
    /**
     * Dashboard üzerinde kullanılan küçük istatistik kartı.
     * Plan, görev, quiz ve başarı metrikleri için ortak kullanılır.
     */

    return (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5 shadow-xl shadow-slate-950/30">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <p className="text-sm text-slate-400">
                        {title}
                    </p>

                    <h3 className="mt-3 text-3xl font-bold text-slate-50">
                        {value}
                    </h3>

                    {description && (
                        <p className="mt-2 text-xs text-slate-500">
                            {description}
                        </p>
                    )}
                </div>

                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-800 text-2xl">
                    {icon}
                </div>
            </div>
        </div>
    );
}

export default StatCard;