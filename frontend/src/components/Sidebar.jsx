// src/components/Sidebar.jsx

const menuItems = [
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

function Sidebar({ activePage, onPageChange }) {
    /**
     * Sol menü bileşeni.
     *
     * Şimdilik react-router kullanmıyoruz.
     * Aktif sayfayı App.jsx içindeki state ile yönetiyoruz.
     */

    return (
        <aside className="hidden min-h-screen w-72 border-r border-slate-800 bg-slate-950 px-5 py-6 lg:block">
            {/* Logo / proje başlığı */}
            <div className="mb-10">
                <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-500/20 text-2xl">
                        🎓
                    </div>

                    <div>
                        <h1 className="text-lg font-bold text-slate-100">
                            Smart Learning
                        </h1>
                        <p className="text-xs text-slate-500">
                            AI Planlayıcı
                        </p>
                    </div>
                </div>
            </div>

            {/* Menü */}
            <nav className="space-y-2">
                {menuItems.map((item) => {
                    const isActive = activePage === item.key;

                    return (
                        <button
                            key={item.key}
                            type="button"
                            onClick={() => onPageChange(item.key)}
                            className={
                                isActive
                                    ? "flex w-full items-center gap-3 rounded-2xl bg-indigo-500 px-4 py-3 text-left text-sm font-semibold text-white shadow-lg shadow-indigo-500/20"
                                    : "flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left text-sm font-medium text-slate-400 transition hover:bg-slate-900 hover:text-slate-100"
                            }
                        >
                            <span className="text-lg">{item.icon}</span>
                            <span>{item.label}</span>
                        </button>
                    );
                })}
            </nav>

            {/* Alt bilgi */}
            <div className="mt-10 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <p className="text-sm font-semibold text-slate-200">
                    MVP Durumu
                </p>
                <p className="mt-2 text-xs leading-5 text-slate-500">
                    Backend aktif, Streamlit test UI çalışıyor. React frontend artık kuruluyor.
                </p>
            </div>
        </aside>
    );
}

export default Sidebar;