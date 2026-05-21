// src/pages/PlanDetailPage.jsx

import YouTubeEmbed from "../components/YouTubeEmbed";
import { useEffect, useState } from "react";
import {
    getPlanById,
    getQuizResultsByPlan,
    updateTaskCompletion,
    regeneratePlanWeek,
    analyzeQuizResult,
} from "../api/apiClient";
import WeeklyQuizPanel from "../components/WeeklyQuizPanel";
import AITutorChat from "../components/AITutorChat";

function PlanDetailPage({ planId, onBack }) {
    /**
     * Seçilen öğrenme planının detay sayfası.
     *
     * Bu sayfada:
     * - Plan özeti
     * - Haftalık öğrenme planı
     * - Görevler
     * - Kaynaklar
     * - Haftalık quiz paneli
     * - Kayıtlı quiz sonuçları
     * gösterilir.
     */

    const [plan, setPlan] = useState(null);
    const [quizResults, setQuizResults] = useState([]);
    const [loading, setLoading] = useState(true);
    const [errorMessage, setErrorMessage] = useState("");

    // Checkbox güncellenirken sadece ilgili görevi kilitlemek için kullanılır.
    // Böylece tüm sayfa tekrar yüklenmez.
    const [updatingTaskIds, setUpdatingTaskIds] = useState([]);

    // Kayıtlı geçmiş quizlerin AI analizi için stateler
    const [loadingAnalyses, setLoadingAnalyses] = useState({});
    const [analysisErrors, setAnalysisErrors] = useState({});

    // Haftaları accordion şeklinde açıp kapatmak için kullanılır.
    // İlk plan yüklendiğinde varsayılan olarak ilk hafta açık olacak.
    const [openWeekIds, setOpenWeekIds] = useState([]);

    // Bir hafta AI ile yeniden oluşturulurken ilgili haftayı kilitlemek için kullanılır.
    const [regeneratingWeekIds, setRegeneratingWeekIds] = useState([]);

    // Her hafta için özel yeniden oluşturma talimatlarını tutar.
    const [regenerateInstructions, setRegenerateInstructions] = useState({});

    // Her hafta için AI ile yenileme kutusunun görünürlüğünü yönetir.
    const [visibleRegenerateBoxes, setVisibleRegenerateBoxes] = useState({});

    async function loadPlanDetail() {
        /**
         * Plan detayını ve bu plana ait quiz sonuçlarını backend'den çeker.
         *
         * Not:
         * - Plan detayı ana veridir.
         * - Quiz sonuçları alınamazsa sayfayı tamamen bozmak yerine boş liste gösteririz.
         */

        try {
            setLoading(true);
            setErrorMessage("");

            const planData = await getPlanById(planId);

            let quizData = [];

            try {
                quizData = await getQuizResultsByPlan(planId);
            } catch (quizError) {
                console.warn("Quiz sonuçları alınamadı:", quizError);
                quizData = [];
            }

            setPlan(planData);
            setQuizResults(quizData);

            // Plan ilk yüklendiğinde sadece ilk haftayı açık yapıyoruz.
            // Kullanıcı daha sonra hafta açıp kapattıysa mevcut accordion durumunu koruyoruz.
            setOpenWeekIds((previousOpenWeekIds) => {
                if (previousOpenWeekIds.length > 0) {
                    return previousOpenWeekIds;
                }

                const firstWeekId = planData.weeks?.[0]?.id;

                return firstWeekId ? [firstWeekId] : [];
            });
        } catch (error) {
            setErrorMessage(error.message || "Plan detayı alınırken hata oluştu.");
        } finally {
            setLoading(false);
        }
    }

    async function handleTaskToggle(taskId, isCompleted) {
        /**
         * Görev checkbox değiştiğinde backend'e güncelleme gönderir.
         *
         * Önemli:
         * - Artık loadPlanDetail() çağırmıyoruz.
         * - Çünkü tüm sayfayı yeniden yüklemek scroll pozisyonunu en üste atıyordu.
         * - Bunun yerine sadece ilgili görevi local state içinde güncelliyoruz.
         */

        const previousPlan = plan;

        try {
            setErrorMessage("");

            setUpdatingTaskIds((previousIds) => [
                ...new Set([...previousIds, taskId]),
            ]);

            // Önce UI tarafında hızlıca güncelliyoruz.
            updateTaskInLocalPlan(taskId, isCompleted);

            // Sonra backend'e kalıcı olarak kaydediyoruz.
            await updateTaskCompletion(taskId, isCompleted);
        } catch (error) {
            // Backend hata verirse eski plan state'ine geri dönüyoruz.
            setPlan(previousPlan);
            setErrorMessage(error.message || "Görev durumu güncellenemedi.");
        } finally {
            setUpdatingTaskIds((previousIds) =>
                previousIds.filter((id) => id !== taskId)
            );
        }
    }

    function toggleRegenerateBox(weekId) {
        /**
         * Seçili hafta için AI ile yenileme kutusunu açıp kapatır.
         *
         * Eğer hafta kapalıysa, kutuyu gösterirken haftayı da açık hale getirir.
         */

        setVisibleRegenerateBoxes((previousValue) => ({
            ...previousValue,
            [weekId]: !previousValue[weekId],
        }));

        setOpenWeekIds((previousOpenWeekIds) => {
            if (previousOpenWeekIds.includes(weekId)) {
                return previousOpenWeekIds;
            }

            return [...previousOpenWeekIds, weekId];
        });
    }

    function updateRegenerateInstruction(weekId, value) {
        /**
         * Her hafta için kullanıcı talimatını ayrı ayrı state içinde tutar.
         */

        setRegenerateInstructions((previousValue) => ({
            ...previousValue,
            [weekId]: value,
        }));
    }

    async function handleRegenerateWeek(weekId) {
        /**
         * Seçili haftayı AI ile yeniden oluşturur.
         *
         * Backend sadece ilgili haftanın:
         * - başlığını
         * - açıklamasını
         * - mini projesini
         * - görevlerini
         * - kaynaklarını
         * günceller.
         */

        if (!plan) {
            return;
        }

        const userInstruction =
            regenerateInstructions[weekId] ||
            "Bu haftayı daha teknik, uygulama odaklı ve kaynakları görevlerle ilişkili olacak şekilde yenile.";

        try {
            setErrorMessage("");

            setRegeneratingWeekIds((previousIds) => [
                ...new Set([...previousIds, weekId]),
            ]);

            const updatedPlan = await regeneratePlanWeek(
                plan.id,
                weekId,
                userInstruction
            );

            setPlan(updatedPlan);

            // Backend ilgili haftaya ait eski quiz sonuçlarını temizlediği için
            // frontend tarafındaki quiz sonuçlarını da güncelliyoruz.
            try {
                const updatedQuizResults = await getQuizResultsByPlan(plan.id);
                setQuizResults(updatedQuizResults);
            } catch (quizError) {
                console.warn("Quiz sonuçları yenilenemedi:", quizError);
            }

            // Yenilenen hafta açık kalsın.
            setOpenWeekIds((previousOpenWeekIds) => {
                if (previousOpenWeekIds.includes(weekId)) {
                    return previousOpenWeekIds;
                }

                return [...previousOpenWeekIds, weekId];
            });

            // İlgili input alanını kapatıyoruz.
            setVisibleRegenerateBoxes((previousValue) => ({
                ...previousValue,
                [weekId]: false,
            }));
        } catch (error) {
            setErrorMessage(error.message || "Hafta AI ile yeniden oluşturulamadı.");
        } finally {
            setRegeneratingWeekIds((previousIds) =>
                previousIds.filter((id) => id !== weekId)
            );
        }
    }

    function getResourceTypeBadge(resourceType) {
        /**
         * Kaynak türüne göre rozet metni ve stil bilgisi döndürür.
         *
         * Amaç:
         * - Kaynak kartlarında tür bilgisini daha okunur göstermek
         * - Dokümantasyon, makale, video ve kurs kaynaklarını görsel olarak ayırmak
         */

        const normalizedType = String(resourceType || "").toLowerCase();

        if (normalizedType.includes("youtube") || normalizedType.includes("video")) {
            return {
                label: "YouTube Video",
                icon: "🎥",
                className: "border-red-500/30 bg-red-500/10 text-red-200",
            };
        }

        if (
            normalizedType.includes("dokümantasyon") ||
            normalizedType.includes("dokumantasyon")
        ) {
            return {
                label: "Dokümantasyon",
                icon: "📘",
                className: "border-sky-500/30 bg-sky-500/10 text-sky-200",
            };
        }

        if (normalizedType.includes("makale")) {
            return {
                label: "Makale",
                icon: "📝",
                className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
            };
        }

        if (normalizedType.includes("kurs")) {
            return {
                label: "Kurs",
                icon: "🎓",
                className: "border-purple-500/30 bg-purple-500/10 text-purple-200",
            };
        }

        return {
            label: resourceType || "Kaynak",
            icon: "🔗",
            className: "border-slate-700 bg-slate-800/70 text-slate-300",
        };
    }

    function calculateProgress() {
        /**
         * Plan içindeki görevlerden lokal ilerleme yüzdesi hesaplar.
         * Backend progress endpointi de kullanılabilir; burada detay verisinden hızlı hesaplıyoruz.
         */

        const weeks = plan?.weeks || [];
        const tasks = weeks.flatMap((week) => week.tasks || []);

        if (tasks.length === 0) {
            return {
                totalTasks: 0,
                completedTasks: 0,
                percentage: 0,
            };
        }

        const completedTasks = tasks.filter((task) => task.is_completed).length;

        return {
            totalTasks: tasks.length,
            completedTasks,
            percentage: Math.round((completedTasks / tasks.length) * 100),
        };
    }

    function updateTaskInLocalPlan(taskId, isCompleted) {
        /**
         * Checkbox değiştiğinde tüm plan detayını yeniden çekmek yerine
         * sadece ilgili görevi local React state içinde günceller.
         *
         * Bu sayede sayfa loading ekranına düşmez ve en üste atmaz.
         */

        setPlan((previousPlan) => {
            if (!previousPlan) {
                return previousPlan;
            }

            return {
                ...previousPlan,
                weeks: previousPlan.weeks.map((week) => ({
                    ...week,
                    tasks: (week.tasks || []).map((task) => {
                        if (task.id !== taskId) {
                            return task;
                        }

                        return {
                            ...task,
                            is_completed: isCompleted,
                        };
                    }),
                })),
            };
        });
    }

    function toggleWeek(weekId) {
        /**
         * Haftayı accordion mantığıyla açıp kapatır.
         */

        setOpenWeekIds((previousOpenWeekIds) => {
            if (previousOpenWeekIds.includes(weekId)) {
                return previousOpenWeekIds.filter((id) => id !== weekId);
            }

            return [...previousOpenWeekIds, weekId];
        });
    }

    async function handleAnalyzeQuizResult(resultId) {
        if (!resultId) return;
        try {
            setLoadingAnalyses((prev) => ({ ...prev, [resultId]: true }));
            setAnalysisErrors((prev) => ({ ...prev, [resultId]: "" }));
            const data = await analyzeQuizResult(resultId);
            
            // Local state'teki quizResults listesini güncelleyerek analizi yerleştiriyoruz.
            setQuizResults((prevResults) =>
                prevResults.map((r) =>
                    r.id === resultId
                        ? { ...r, analysis_json: JSON.stringify(data) }
                        : r
                )
            );
        } catch (error) {
            setAnalysisErrors((prev) => ({
                ...prev,
                [resultId]: error.message || "Analiz yüklenirken hata oluştu.",
            }));
        } finally {
            setLoadingAnalyses((prev) => ({ ...prev, [resultId]: false }));
        }
    }

    useEffect(() => {
        /**
         * PlanDetailPage ilk açıldığında veya planId değiştiğinde
         * seçilen planın detaylarını backend'den yüklüyoruz.
         */

        if (!planId) {
            setErrorMessage("Plan ID bulunamadı.");
            setLoading(false);
            return;
        }

        loadPlanDetail();
    }, [planId]);

    if (loading) {
        return (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8">
                <p className="text-slate-400">Plan detayı yükleniyor...</p>
            </div>
        );
    }

    if (errorMessage) {
        return (
            <div className="rounded-3xl border border-red-900/60 bg-red-950/40 p-8">
                <h2 className="text-2xl font-bold text-red-200">
                    Plan detayı alınamadı
                </h2>

                <p className="mt-3 text-red-200/80">{errorMessage}</p>

                <button
                    type="button"
                    onClick={onBack}
                    className="mt-5 rounded-2xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:text-white"
                >
                    Planlara Dön
                </button>
            </div>
        );
    }

    if (!plan) {
        return null;
    }

    const progress = calculateProgress();

    return (
        <div className="space-y-8">
            {/* Üst navigasyon */}
            <button
                type="button"
                onClick={onBack}
                className="rounded-2xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 transition hover:border-indigo-500 hover:text-white"
            >
                ← Planlara Dön
            </button>

            {/* Plan özeti */}
            <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl shadow-slate-950/30">
                <p className="text-sm font-semibold text-indigo-300">{plan.level}</p>

                <h2 className="mt-2 text-4xl font-bold text-slate-50">
                    {plan.topic}
                </h2>

                <p className="mt-4 max-w-4xl text-sm leading-6 text-slate-400">
                    {plan.summary || plan.goal}
                </p>

                {plan.final_outcome && (
                    <div className="mt-5 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4">
                        <p className="text-sm font-semibold text-emerald-200">
                            Plan Sonu Kazanım
                        </p>

                        <p className="mt-2 text-sm leading-6 text-emerald-100/80">
                            {plan.final_outcome}
                        </p>
                    </div>
                )}

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
                        <p className="text-xs text-slate-500">Tamamlanan Görev</p>
                        <p className="mt-1 text-lg font-bold text-slate-100">
                            {progress.completedTasks}/{progress.totalTasks}
                        </p>
                    </div>

                    <div className="rounded-2xl bg-slate-950/60 p-4">
                        <p className="text-xs text-slate-500">İlerleme</p>
                        <p className="mt-1 text-lg font-bold text-slate-100">
                            %{progress.percentage}
                        </p>
                    </div>
                </div>

                <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-800">
                    <div
                        className="h-full rounded-full bg-indigo-500"
                        style={{ width: `${progress.percentage}%` }}
                    />
                </div>
            </section>

            {/* Haftalık plan */}
            <section>
                <h3 className="mb-4 text-2xl font-bold text-slate-100">
                    Haftalık Öğrenme Planı
                </h3>

                <div className="space-y-5">
                    {plan.weeks?.map((week) => {
                        const isWeekOpen = openWeekIds.includes(week.id);
                        const weekTasks = week.tasks || [];
                        const completedWeekTasks = weekTasks.filter(
                            (task) => task.is_completed
                        ).length;
                        const weekResources = week.resources || [];
                        const isRegenerating = regeneratingWeekIds.includes(week.id);

                        return (
                            <div
                                key={week.id}
                                className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6"
                            >
                                {/* Accordion başlığı */}
                                <div className="flex w-full flex-col gap-4 md:flex-row md:items-start md:justify-between">
                                    <button
                                        type="button"
                                        onClick={() => toggleWeek(week.id)}
                                        className="text-left"
                                    >
                                        <p className="text-sm font-semibold text-indigo-300">
                                            Hafta {week.week_number}
                                        </p>

                                        <h4 className="mt-1 text-2xl font-bold text-slate-50">
                                            {week.title}
                                        </h4>

                                        <p className="mt-2 text-sm text-slate-500">
                                            {completedWeekTasks}/{weekTasks.length} görev tamamlandı ·{" "}
                                            {weekResources.length} kaynak
                                        </p>
                                    </button>

                                    <div className="flex flex-wrap items-center gap-3">
                                        <button
                                            type="button"
                                            disabled={isRegenerating}
                                            onClick={() => toggleRegenerateBox(week.id)}
                                            className="rounded-full border border-purple-500/40 bg-purple-500/10 px-4 py-2 text-sm font-bold text-purple-200 transition hover:bg-purple-500 hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            AI ile Yenile
                                        </button>

                                        <span className="w-fit rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-slate-300">
                                            {week.estimated_hours || plan.weekly_hours} saat
                                        </span>

                                        <button
                                            type="button"
                                            onClick={() => toggleWeek(week.id)}
                                            className="flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950 text-lg text-slate-300 transition hover:border-indigo-500/50"
                                        >
                                            {isWeekOpen ? "−" : "+"}
                                        </button>
                                    </div>
                                </div>

                                {/* Accordion içeriği */}
                                {isWeekOpen && (
                                    <div className="mt-6">
                                        {visibleRegenerateBoxes[week.id] && (
                                            <div className="mb-6 rounded-2xl border border-purple-500/20 bg-purple-500/10 p-4">
                                                <p className="text-sm font-bold text-purple-100">
                                                    Bu haftayı AI ile yeniden düzenle
                                                </p>

                                                <p className="mt-2 text-sm text-purple-100/70">
                                                    Örneğin: “Bu haftayı daha uygulama ağırlıklı yap”,
                                                    “Görevleri ileri seviyeye çek” veya “Kaynakları daha
                                                    teknik hale getir.”
                                                </p>

                                                <textarea
                                                    value={regenerateInstructions[week.id] || ""}
                                                    onChange={(event) =>
                                                        updateRegenerateInstruction(
                                                            week.id,
                                                            event.target.value
                                                        )
                                                    }
                                                    placeholder="Bu haftayı daha uygulama ağırlıklı yap. Görevleri daha teknik, kaynakları görevlerle doğrudan ilişkili olacak şekilde yenile."
                                                    className="mt-4 min-h-28 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-purple-400"
                                                />

                                                <div className="mt-4 flex flex-wrap gap-3">
                                                    <button
                                                        type="button"
                                                        disabled={isRegenerating}
                                                        onClick={() => handleRegenerateWeek(week.id)}
                                                        className="rounded-xl bg-purple-500 px-4 py-2 text-sm font-bold text-white transition hover:bg-purple-400 disabled:cursor-not-allowed disabled:opacity-60"
                                                    >
                                                        {isRegenerating ? "Yenileniyor..." : "Haftayı Yenile"}
                                                    </button>

                                                    <button
                                                        type="button"
                                                        disabled={isRegenerating}
                                                        onClick={() => toggleRegenerateBox(week.id)}
                                                        className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-bold text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                                                    >
                                                        Vazgeç
                                                    </button>
                                                </div>
                                            </div>
                                        )}

                                        <p className="text-sm leading-6 text-slate-400">
                                            {week.description}
                                        </p>

                                        {week.mini_project && (
                                            <div className="mt-5 rounded-2xl border border-sky-500/20 bg-sky-500/10 p-4">
                                                <p className="text-sm font-semibold text-sky-200">
                                                    Mini Proje
                                                </p>

                                                <p className="mt-2 text-sm leading-6 text-sky-100/80">
                                                    {week.mini_project}
                                                </p>
                                            </div>
                                        )}

                                        {/* Görevler */}
                                        <div className="mt-6">
                                            <h5 className="font-bold text-slate-100">Görevler</h5>

                                            <div className="mt-3 space-y-3">
                                                {weekTasks.map((task) => (
                                                    <label
                                                        key={task.id}
                                                        className="flex cursor-pointer items-start gap-3 rounded-2xl border border-slate-800 bg-slate-950/50 p-4 transition hover:border-indigo-500/50"
                                                    >
                                                        <input
                                                            type="checkbox"
                                                            checked={Boolean(task.is_completed)}
                                                            disabled={updatingTaskIds.includes(task.id)}
                                                            onChange={(event) =>
                                                                handleTaskToggle(task.id, event.target.checked)
                                                            }
                                                            className="mt-1 h-4 w-4 accent-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                                                        />

                                                        <div className="flex-1">
                                                            <p
                                                                className={
                                                                    task.is_completed
                                                                        ? "text-sm font-semibold text-slate-500 line-through"
                                                                        : "text-sm font-semibold text-slate-100"
                                                                }
                                                            >
                                                                {task.task_text}
                                                            </p>

                                                            <p className="mt-2 text-xs text-slate-500">
                                                                {task.task_type || "Görev"} |{" "}
                                                                {task.estimated_minutes || 0} dk |{" "}
                                                                {task.difficulty || "Orta"}
                                                            </p>
                                                        </div>
                                                    </label>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Kaynaklar */}
                                        <div className="mt-6">
                                            <h5 className="font-bold text-slate-100">Kaynaklar</h5>

                                            <div className="mt-3 grid gap-3 md:grid-cols-2">
                                                {weekResources.map((resource) => {
                                                    const badge = getResourceTypeBadge(
                                                        resource.resource_type
                                                    );

                                                    return (
                                                        <div
                                                            key={resource.id}
                                                            className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4"
                                                        >
                                                            <p className="text-sm font-bold text-slate-100">
                                                                {resource.resource_title}
                                                            </p>

                                                            <span
                                                                className={`mt-3 inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1 text-xs font-bold ${badge.className}`}
                                                            >
                                                                <span>{badge.icon}</span>
                                                                <span>{badge.label}</span>
                                                            </span>

                                                            <p className="mt-4 text-sm leading-6 text-slate-400">
                                                                {resource.resource_description}
                                                            </p>

                                                            <YouTubeEmbed
                                                                url={resource.resource_url}
                                                                title={resource.resource_title}
                                                            />

                                                            {resource.resource_url && (
                                                                <a
                                                                    href={resource.resource_url}
                                                                    target="_blank"
                                                                    rel="noreferrer"
                                                                    className="mt-4 inline-flex rounded-xl border border-indigo-500/40 px-3 py-2 text-sm font-semibold text-indigo-200 transition hover:bg-indigo-500 hover:text-white"
                                                                >
                                                                    Kaynağı Aç
                                                                </a>
                                                            )}
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>

                                        {/* Haftalık quiz oluşturma ve çözme paneli */}
                                        <WeeklyQuizPanel
                                            planId={plan.id}
                                            week={week}
                                            onQuizSaved={loadPlanDetail}
                                        />
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </section>

            {/* Kayıtlı quiz sonuçları */}
            <section>
                <h3 className="mb-4 text-2xl font-bold text-slate-100">
                    Kaydedilmiş Quiz Sonuçları
                </h3>

                {quizResults.length === 0 ? (
                    <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
                        <p className="text-slate-400">
                            Bu plan için henüz kaydedilmiş quiz sonucu yok.
                        </p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {quizResults.map((result) => (
                            <div
                                key={result.id}
                                className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6"
                            >
                                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                                    <div>
                                        <h4 className="text-lg font-bold text-slate-100">
                                            {result.quiz_title}
                                        </h4>

                                        <p className="mt-1 text-sm text-slate-500">
                                            {result.created_at?.slice(0, 19).replace("T", " ")}
                                        </p>
                                    </div>

                                    <div className="rounded-2xl bg-slate-950/60 px-5 py-3">
                                        <p className="text-xs text-slate-500">Skor</p>
                                        <p className="text-xl font-bold text-slate-100">
                                            {result.correct_count}/{result.total_questions} - %
                                            {result.score_percentage}
                                        </p>
                                    </div>
                                </div>

                                {result.details_json && (
                                    <details className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
                                        <summary className="cursor-pointer text-sm font-semibold text-indigo-200">
                                            Soru ve cevap detaylarını göster
                                        </summary>

                                        <QuizDetails detailsJson={result.details_json} />
                                    </details>
                                )}

                                {/* Zayıf Konular Analizi Butonu & Kartı */}
                                {result.score_percentage < 100 && (
                                    <div className="mt-4 pt-4 border-t border-slate-800/60">
                                        {!result.analysis_json ? (
                                            <button
                                                type="button"
                                                onClick={() => handleAnalyzeQuizResult(result.id)}
                                                disabled={loadingAnalyses[result.id]}
                                                className="w-full rounded-2xl bg-gradient-to-r from-amber-500 to-orange-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-orange-500/20 transition hover:from-amber-400 hover:to-orange-500 disabled:cursor-not-allowed disabled:opacity-60 cursor-pointer"
                                            >
                                                {loadingAnalyses[result.id]
                                                    ? "Zayıf Konular Analiz Ediliyor..."
                                                    : "🔍 AI ile Zayıf Konuları Analiz Et"}
                                            </button>
                                        ) : (
                                            (() => {
                                                let analysis = null;
                                                try {
                                                    analysis =
                                                        typeof result.analysis_json === "string"
                                                            ? JSON.parse(result.analysis_json)
                                                            : result.analysis_json;
                                                } catch (e) {
                                                    analysis = null;
                                                }
                                                if (!analysis) return null;
                                                return (
                                                    <div className="mt-3 rounded-2xl border border-indigo-500/20 bg-indigo-950/20 p-4">
                                                        <h6 className="text-sm font-bold text-indigo-300 flex items-center gap-2">
                                                            💡 Yapay Zekâ Analiz Raporu
                                                        </h6>

                                                        <p className="mt-2 text-xs text-slate-300 italic">
                                                            "{analysis.summary}"
                                                        </p>

                                                        {analysis.weak_topics &&
                                                            analysis.weak_topics.length > 0 && (
                                                                <div className="mt-3">
                                                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                                                        Tespit Edilen Zayıf Konular
                                                                    </span>
                                                                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                                                                        {analysis.weak_topics.map((topic, i) => (
                                                                            <span
                                                                                key={i}
                                                                                className="rounded-lg bg-red-500/10 border border-red-500/30 px-2 py-0.5 text-[10px] font-semibold text-red-200"
                                                                            >
                                                                                ⚠️ {topic}
                                                                            </span>
                                                                        ))}
                                                                    </div>
                                                                </div>
                                                            )}

                                                        {analysis.recommended_actions &&
                                                            analysis.recommended_actions.length > 0 && (
                                                                <div className="mt-3">
                                                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                                                        Gelişim Önerileri
                                                                    </span>
                                                                    <ul className="mt-1 space-y-1 text-xs text-slate-300 list-disc list-inside">
                                                                        {analysis.recommended_actions.map((action, i) => (
                                                                            <li key={i}>{action}</li>
                                                                        ))}
                                                                    </ul>
                                                                </div>
                                                            )}

                                                        {analysis.recommended_resources &&
                                                            analysis.recommended_resources.length > 0 && (
                                                                <div className="mt-3 pt-3 border-t border-slate-800">
                                                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                                                        Önerilen Arama Terimleri / Kaynaklar
                                                                    </span>
                                                                    <ul className="mt-1 space-y-1 text-xs text-indigo-200">
                                                                        {analysis.recommended_resources.map(
                                                                            (resItem, i) => (
                                                                                <li key={i} className="flex items-start gap-1.5">
                                                                                    <span>🔍</span>
                                                                                    <span>{resItem}</span>
                                                                                </li>
                                                                            )
                                                                        )}
                                                                    </ul>
                                                                </div>
                                                            )}
                                                    </div>
                                                );
                                            })()
                                        )}

                                        {analysisErrors[result.id] && (
                                            <div className="mt-2 rounded-xl border border-red-900/60 bg-red-950/40 px-3 py-2 text-[10px] text-red-200">
                                                {analysisErrors[result.id]}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* AI Tutor Chatbot */}
            <AITutorChat plan={plan} weeks={plan.weeks} openWeekIds={openWeekIds} />
        </div>
    );
}

function QuizDetails({ detailsJson }) {
    /**
     * details_json içindeki soru-cevap detaylarını parse edip gösterir.
     */

    let details = [];

    try {
        details = JSON.parse(detailsJson);
    } catch {
        details = [];
    }

    if (!details.length) {
        return (
            <p className="mt-4 text-sm text-slate-500">
                Detay verisi okunamadı.
            </p>
        );
    }

    return (
        <div className="mt-4 space-y-3">
            {details.map((item) => (
                <div
                    key={item.question_number}
                    className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"
                >
                    <p
                        className={
                            item.is_correct
                                ? "text-sm font-bold text-emerald-300"
                                : "text-sm font-bold text-red-300"
                        }
                    >
                        Soru {item.question_number}:{" "}
                        {item.is_correct ? "Doğru" : "Yanlış"}
                    </p>

                    <p className="mt-3 text-sm font-semibold text-slate-100">
                        {item.question}
                    </p>

                    <p className="mt-3 text-sm text-slate-400">
                        <strong>Senin cevabın:</strong>{" "}
                        {item.selected_answer || "Boş"}
                    </p>

                    <p className="mt-1 text-sm text-slate-400">
                        <strong>Doğru cevap:</strong> {item.correct_answer}
                    </p>

                    <p className="mt-3 rounded-xl bg-sky-500/10 p-3 text-sm text-sky-100/80">
                        {item.explanation}
                    </p>
                </div>
            ))}
        </div>
    );
}

export default PlanDetailPage;