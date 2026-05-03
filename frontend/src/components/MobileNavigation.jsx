// src/components/MobileNavigation.jsx

const mobileMenuItems = [
    {
        key: "dashboard",
        label: "Dashboard",
        icon: "📊",
    },
    {
        key: "plan-create",
        label: "Plan Oluştur",
        icon: "✨",
    },
    {
        key: "my-plans",
        label: "Planlarım",
        icon: "📚",
    },
    {
        key: "quiz-results",
        label: "Quiz Sonuçları",
        icon: "🧪",
    },
    {
        key: "resources",
        label: "Resources",
        icon: "🔗",
    },
];

function MobileNavigation({ activePage, onPageChange }) {
    /**
     * Küçük ekranlar için üst navigasyon bileşeni.
     *
     * Sidebar componenti lg breakpoint altında gizlendiği için,
     * mobil/tablet görünümde kullanıcı sayfalar arasında buradan geçiş yapar.
     */

    function getActiveLabel() {
        /**
         * Aktif sayfanın başlığını bulur.
         * Plan detay sayfası sidebar menüsünde olmadığı için ayrı ele alıyoruz.
         */

        if (activePage === "plan-detail") {
            return "Plan Detayı";
        }

        const activeItem = mobileMenuItems.find((item) => item.key === activePage);

        return activeItem?.label || "Dashboard";
    }

    return (
        <div className="mb-6 rounded-3xl border border-slate-800 bg-slate-900/80 p-4 shadow-xl shadow-slate-950/30 lg:hidden">
            {/* Mobil üst başlık */}
            <div className="flex items-center justify-between gap-4">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Smart Learning
                    </p>

                    <h1 className="mt-1 text-xl font-bold text-slate-50">
                        {getActiveLabel()}
                    </h1>
                </div>

                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-500/20 text-2xl">
                    🎓
                </div>
            </div>

            {/* Mobil yatay menü */}
            <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
                {mobileMenuItems.map((item) => {
                    const isActive = activePage === item.key;

                    return (
                        <button
                            key={item.key}
                            type="button"
                            onClick={() => onPageChange(item.key)}
                            className={
                                isActive
                                    ? "flex shrink-0 items-center gap-2 rounded-2xl bg-indigo-500 px-4 py-2 text-sm font-bold text-white"
                                    : "flex shrink-0 items-center gap-2 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-2 text-sm font-semibold text-slate-400"
                            }
                        >
                            <span>{item.icon}</span>
                            <span>{item.label}</span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

export default MobileNavigation;