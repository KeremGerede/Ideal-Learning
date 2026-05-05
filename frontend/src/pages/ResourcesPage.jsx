// src/pages/ResourcesPage.jsx

import YouTubeEmbed from "../components/YouTubeEmbed";
import { useEffect, useMemo, useState } from "react";
import { getAllPlans } from "../api/apiClient";

function ResourcesPage() {
    /**
     * Tüm öğrenme planlarındaki kaynakları tek sayfada listeler.
     *
     * Backend'de kaynaklar haftalara bağlı tutuluyor.
     * Bu sayfada tüm planları çekip:
     * plan -> weeks -> resources
     * yapısından düz bir kaynak listesi oluşturuyoruz.
     *
     * Sonrasında kaynakları seçilen hedefe / plana göre grupluyoruz.
     */

    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [errorMessage, setErrorMessage] = useState("");
    const [searchText, setSearchText] = useState("");
    const [selectedType, setSelectedType] = useState("Tümü");
    const [selectedGoal, setSelectedGoal] = useState("Tümü");

    async function loadPlans() {
        /**
         * Backend'den tüm planları çeker.
         *
         * Kaynaklar planların haftaları içinde geldiği için
         * ayrı bir resources endpoint'ine şu an ihtiyaç duymuyoruz.
         */

        try {
            setLoading(true);
            setErrorMessage("");

            const plansData = await getAllPlans();
            setPlans(plansData);
        } catch (error) {
            setErrorMessage(error.message || "Kaynaklar alınırken hata oluştu.");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        /**
         * Sayfa ilk açıldığında planları ve dolayısıyla kaynakları yüklüyoruz.
         */

        loadPlans();
    }, []);

    const resources = useMemo(() => {
        /**
         * Planlar içindeki haftalık kaynakları tek düz listeye çevirir.
         *
         * Her kaynak nesnesine ayrıca:
         * - plan_id
         * - plan_topic
         * - plan_goal
         * - plan_level
         * - week_id
         * - week_number
         * - week_title
         * bilgilerini ekliyoruz.
         */

        const collectedResources = [];

        plans.forEach((plan) => {
            const weeks = plan.weeks || [];

            weeks.forEach((week) => {
                const weekResources = week.resources || [];

                weekResources.forEach((resource) => {
                    collectedResources.push({
                        ...resource,

                        // Kaynağın hangi plana/hedefe ait olduğunu saklıyoruz.
                        // Bu bilgi Resources sayfasında hedef bazlı gruplama için kullanılır.
                        plan_id: plan.id,
                        plan_topic: plan.topic,
                        plan_goal: plan.goal,
                        plan_level: plan.level,

                        week_id: week.id,
                        week_number: week.week_number,
                        week_title: week.title,
                    });
                });
            });
        });

        return collectedResources;
    }, [plans]);

    const resourceTypes = useMemo(() => {
        /**
         * Kaynak tipi filtresi için unique kaynak tiplerini çıkarır.
         */

        const types = new Set();

        resources.forEach((resource) => {
            if (resource.resource_type) {
                types.add(resource.resource_type);
            }
        });

        return ["Tümü", ...Array.from(types)];
    }, [resources]);

    const goalOptions = useMemo(() => {
        /**
         * Hedef / plan filtresi için planları tekilleştirir.
         *
         * Aynı plan birden fazla kaynak içerdiği için,
         * kaynaklardan plan_id bazlı unique hedef listesi çıkarıyoruz.
         */

        const goalsMap = new Map();

        resources.forEach((resource) => {
            if (!goalsMap.has(resource.plan_id)) {
                goalsMap.set(resource.plan_id, {
                    value: String(resource.plan_id),
                    label: `${resource.plan_topic} - ${resource.plan_goal || "Hedef belirtilmedi"}`,
                });
            }
        });

        return [
            {
                value: "Tümü",
                label: "Tüm hedefler",
            },
            ...Array.from(goalsMap.values()),
        ];
    }, [resources]);

    const filteredResources = resources.filter((resource) => {
        /**
         * Arama, kaynak tipi filtresi ve hedef/plan filtresini uygular.
         */

        const query = searchText.toLowerCase();

        const matchesSearch =
            resource.resource_title?.toLowerCase().includes(query) ||
            resource.resource_description?.toLowerCase().includes(query) ||
            resource.resource_type?.toLowerCase().includes(query) ||
            resource.plan_topic?.toLowerCase().includes(query) ||
            resource.plan_goal?.toLowerCase().includes(query) ||
            resource.week_title?.toLowerCase().includes(query);

        const matchesType =
            selectedType === "Tümü" || resource.resource_type === selectedType;

        const matchesGoal =
            selectedGoal === "Tümü" || String(resource.plan_id) === selectedGoal;

        return matchesSearch && matchesType && matchesGoal;
    });

    const groupedResources = useMemo(() => {
        /**
         * Filtrelenen kaynakları plan/hedef bazında gruplar.
         *
         * Her grup:
         * - plan_id
         * - plan_topic
         * - plan_goal
         * - plan_level
         * - resources
         * bilgilerini içerir.
         */

        const groupsMap = new Map();

        filteredResources.forEach((resource) => {
            const groupKey = resource.plan_id;

            if (!groupsMap.has(groupKey)) {
                groupsMap.set(groupKey, {
                    plan_id: resource.plan_id,
                    plan_topic: resource.plan_topic,
                    plan_goal: resource.plan_goal,
                    plan_level: resource.plan_level,
                    resources: [],
                });
            }

            groupsMap.get(groupKey).resources.push(resource);
        });

        return Array.from(groupsMap.values());
    }, [filteredResources]);

    if (loading) {
        return (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8">
                <p className="text-slate-400">
                    Kaynaklar yükleniyor...
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Sayfa başlığı */}
            <section>
                <div className="inline-flex rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-sm text-indigo-200">
                    Öğrenme kaynakları
                </div>

                <h2 className="mt-5 text-4xl font-bold tracking-tight text-slate-50 md:text-5xl">
                    Resources
                </h2>

                <p className="mt-4 max-w-2xl text-slate-400">
                    Tüm öğrenme planlarındaki dokümantasyon, video, kurs, makale ve uygulama kaynaklarını hedeflere göre gruplandırılmış şekilde inceleyebilirsin.
                </p>
            </section>

            {/* Hata mesajı */}
            {errorMessage && (
                <div className="rounded-2xl border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                    {errorMessage}
                </div>
            )}

            {/* Özet kartları */}
            <section className="grid gap-4 md:grid-cols-3">
                <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
                    <p className="text-sm text-slate-400">
                        Toplam Kaynak
                    </p>

                    <p className="mt-3 text-3xl font-bold text-slate-50">
                        {resources.length}
                    </p>
                </div>

                <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
                    <p className="text-sm text-slate-400">
                        Kaynak Tipi
                    </p>

                    <p className="mt-3 text-3xl font-bold text-slate-50">
                        {resourceTypes.length - 1}
                    </p>
                </div>

                <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
                    <p className="text-sm text-slate-400">
                        Bağlı Plan
                    </p>

                    <p className="mt-3 text-3xl font-bold text-slate-50">
                        {plans.length}
                    </p>
                </div>
            </section>

            {/* Arama ve filtre alanı */}
            <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
                <div className="grid gap-4 md:grid-cols-[2fr_1fr_1fr]">
                    <div>
                        <label className="text-sm font-semibold text-slate-200">
                            Kaynak ara
                        </label>

                        <input
                            type="text"
                            value={searchText}
                            onChange={(event) => setSearchText(event.target.value)}
                            placeholder="Kaynak adı, açıklama, plan konusu, hedef veya hafta başlığı ile ara"
                            className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-indigo-500"
                        />
                    </div>

                    <div>
                        <label className="text-sm font-semibold text-slate-200">
                            Kaynak tipi
                        </label>

                        <select
                            value={selectedType}
                            onChange={(event) => setSelectedType(event.target.value)}
                            className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-500"
                        >
                            {resourceTypes.map((type) => (
                                <option key={type} value={type}>
                                    {type}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="text-sm font-semibold text-slate-200">
                            Hedef / Plan
                        </label>

                        <select
                            value={selectedGoal}
                            onChange={(event) => setSelectedGoal(event.target.value)}
                            className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-500"
                        >
                            {goalOptions.map((goal) => (
                                <option key={goal.value} value={goal.value}>
                                    {goal.label}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>
            </section>

            {/* Boş durum */}
            {filteredResources.length === 0 && (
                <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8">
                    <h3 className="text-xl font-bold text-slate-100">
                        Kaynak bulunamadı
                    </h3>

                    <p className="mt-3 text-slate-400">
                        Henüz kayıtlı kaynak yok veya arama kriterine uygun kaynak bulunamadı.
                    </p>
                </div>
            )}

            {/* Hedef / plan bazlı gruplandırılmış kaynak listesi */}
            {filteredResources.length > 0 && (
                <section className="space-y-8">
                    {groupedResources.map((group) => (
                        <div
                            key={group.plan_id}
                            className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6"
                        >
                            {/* Grup başlığı */}
                            <div className="mb-5">
                                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                                    <div>
                                        <p className="text-sm font-semibold text-indigo-300">
                                            {group.plan_level || "Seviye belirtilmedi"}
                                        </p>

                                        <h3 className="mt-1 text-2xl font-bold text-slate-50">
                                            {group.plan_topic}
                                        </h3>

                                        <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">
                                            <span className="font-semibold text-slate-300">
                                                Hedef:
                                            </span>{" "}
                                            {group.plan_goal || "Hedef belirtilmedi"}
                                        </p>
                                    </div>

                                    <span className="w-fit rounded-2xl bg-slate-950 px-4 py-2 text-sm font-semibold text-slate-300">
                                        {group.resources.length} kaynak
                                    </span>
                                </div>
                            </div>

                            {/* Grup içindeki kaynaklar */}
                            <div className="grid gap-5 xl:grid-cols-2">
                                {group.resources.map((resource) => (
                                    <ResourceCard
                                        key={`${resource.plan_id}-${resource.week_id}-${resource.id}`}
                                        resource={resource}
                                    />
                                ))}
                            </div>
                        </div>
                    ))}
                </section>
            )}
        </div>
    );
}

function ResourceCard({ resource }) {
    /**
     * Tek bir öğrenme kaynağını kart olarak gösterir.
     */

    return (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl shadow-slate-950/30">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                    <p className="text-sm font-semibold text-indigo-300">
                        {resource.resource_type || "Kaynak"}
                    </p>

                    <h3 className="mt-2 text-xl font-bold text-slate-50">
                        {resource.resource_title}
                    </h3>
                </div>

                {resource.resource_url ? (
                    <a
                        href={resource.resource_url}
                        target="_blank"
                        rel="noreferrer"
                        className="w-fit rounded-2xl border border-indigo-500/40 px-4 py-2 text-sm font-semibold text-indigo-200 transition hover:bg-indigo-500 hover:text-white"
                    >
                        Kaynağı Aç
                    </a>
                ) : (
                    <span className="w-fit rounded-2xl border border-slate-800 px-4 py-2 text-sm font-semibold text-slate-500">
                        Link yok
                    </span>
                )}
            </div>

            <p className="mt-4 text-sm leading-6 text-slate-400">
                {resource.resource_description || "Açıklama bulunamadı."}
            </p>

            {/* YouTube kaynakları için video önizleme/player gösteriyoruz. */}
            <YouTubeEmbed
                url={resource.resource_url}
                title={resource.resource_title}
            />

            <div className="mt-5 grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl bg-slate-950/60 p-4">
                    <p className="text-xs text-slate-500">
                        Plan
                    </p>

                    <p className="mt-1 text-sm font-bold text-slate-100">
                        {resource.plan_topic}
                    </p>
                </div>

                <div className="rounded-2xl bg-slate-950/60 p-4">
                    <p className="text-xs text-slate-500">
                        Hafta
                    </p>

                    <p className="mt-1 text-sm font-bold text-slate-100">
                        Hafta {resource.week_number}: {resource.week_title}
                    </p>
                </div>
            </div>
        </div>
    );
}

export default ResourcesPage;