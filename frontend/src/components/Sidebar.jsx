// src/components/Sidebar.jsx

import { useAuth } from "../context/AuthContext";

const menuItems = [
    { key: "dashboard",    label: "Dashboard",      icon: "📊" },
    { key: "plan-create",  label: "Plan Oluştur",   icon: "✨" },
    { key: "my-plans",     label: "Planlarım",      icon: "📚" },
    { key: "quiz-results", label: "Quiz Sonuçları", icon: "🧪" },
    { key: "resources",    label: "Resources",      icon: "🔗" },
];

function Sidebar({ activePage, onPageChange }) {
    const { user, logout } = useAuth();

    return (
        <aside className="hidden min-h-screen w-72 flex-col border-r border-slate-800 bg-slate-950 px-5 py-6 lg:flex">
            {/* Logo / proje başlığı */}
            <div className="mb-10">
                <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-500/20 text-2xl">
                        🎓
                    </div>
                    <div>
                        <h1 className="text-lg font-bold text-slate-100">Smart Learning</h1>
                        <p className="text-xs text-slate-500">AI Planlayıcı</p>
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

            {/* Spacer */}
            <div className="flex-1" />

            {/* Kullanıcı bilgisi ve çıkış */}
            <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-slate-200">
                            {user?.username ?? "Kullanıcı"}
                        </p>
                        <p className="truncate text-xs text-slate-500">
                            {user?.email ?? ""}
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={logout}
                        title="Çıkış Yap"
                        className="flex-shrink-0 rounded-xl bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-300 transition hover:bg-red-900/40 hover:text-red-300"
                    >
                        Çıkış
                    </button>
                </div>
            </div>
        </aside>
    );
}

export default Sidebar;
