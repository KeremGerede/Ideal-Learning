// src/pages/QuizResultsPage.jsx

import { useEffect, useState } from "react";
import { getAllQuizResults, analyzeQuizResult, adaptPlanFromQuiz } from "../api/apiClient";

function QuizResultsPage() {
    /**
     * Kaydedilmiş tüm quiz sonuçlarını gösteren sayfa.
     *
     * Bu sayfada:
     * - Quiz başlığı
     * - Plan ID / Hafta ID
     * - Skor
     * - Başarı yüzdesi
     * - Tarih
     * - Soru/cevap detayları
     * gösterilir.
     */

    const [quizResults, setQuizResults] = useState([]);
    const [loading, setLoading] = useState(true);
    const [errorMessage, setErrorMessage] = useState("");
    const [searchText, setSearchText] = useState("");

    async function loadQuizResults() {
        /**
         * Backend'den tüm kayıtlı quiz sonuçlarını çeker.
         */

        try {
            setLoading(true);
            setErrorMessage("");

            const results = await getAllQuizResults();
            setQuizResults(results);
        } catch (error) {
            setErrorMessage(error.message || "Quiz sonuçları alınırken hata oluştu.");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        /**
         * Sayfa ilk açıldığında quiz sonuçlarını yüklüyoruz.
         */

        loadQuizResults();
    }, []);

    const filteredResults = quizResults.filter((result) => {
        const query = searchText.toLowerCase();

        return (
            result.quiz_title?.toLowerCase().includes(query) ||
            String(result.plan_id).includes(query) ||
            String(result.week_id).includes(query)
        );
    });

    if (loading) {
        return (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8">
                <p className="text-slate-400">
                    Quiz sonuçları yükleniyor...
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Sayfa başlığı */}
            <section>
                <div className="inline-flex rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-sm text-indigo-200">
                    Ölçme ve değerlendirme
                </div>

                <h2 className="mt-5 text-4xl font-bold tracking-tight text-slate-50 md:text-5xl">
                    Quiz Sonuçları
                </h2>

                <p className="mt-4 max-w-2xl text-slate-400">
                    Daha önce çözülen quizlerin skorlarını, başarı oranlarını ve soru-cevap detaylarını buradan inceleyebilirsin.
                </p>
            </section>

            {/* Hata mesajı */}
            {errorMessage && (
                <div className="rounded-2xl border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                    {errorMessage}
                </div>
            )}

            {/* Arama alanı */}
            <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
                <label className="text-sm font-semibold text-slate-200">
                    Quiz ara
                </label>

                <input
                    type="text"
                    value={searchText}
                    onChange={(event) => setSearchText(event.target.value)}
                    placeholder="Quiz başlığı, plan ID veya hafta ID ile ara"
                    className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-indigo-500"
                />
            </section>

            {/* Boş durum */}
            {filteredResults.length === 0 && (
                <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8">
                    <h3 className="text-xl font-bold text-slate-100">
                        Quiz sonucu bulunamadı
                    </h3>

                    <p className="mt-3 text-slate-400">
                        Henüz kaydedilmiş quiz sonucu yok veya arama kriterine uyan sonuç bulunamadı.
                    </p>
                </div>
            )}

            {/* Quiz sonuç listesi */}
            {filteredResults.length > 0 && (
                <section className="space-y-5">
                    {filteredResults.map((result) => (
                        <QuizResultCard
                            key={result.id}
                            result={result}
                        />
                    ))}
                </section>
            )}
        </div>
    );
}

function QuizResultCard({ result }) {
    /**
     * Tek bir quiz sonucunu kart olarak gösterir.
     */

    const score = result.score_percentage ?? 0;

    // Parse initial analysis if it exists in result.analysis_json
    const initialAnalysis = (() => {
        if (result.analysis_json) {
            try {
                return JSON.parse(result.analysis_json);
            } catch (e) {
                console.error("Failed to parse analysis_json", e);
            }
        }
        return null;
    })();

    const [analysis, setAnalysis] = useState(initialAnalysis);
    const [loadingAnalysis, setLoadingAnalysis] = useState(false);
    const [analysisError, setAnalysisError] = useState("");

    async function handleAnalyzeQuiz() {
        if (!result.id) return;
        try {
            setLoadingAnalysis(true);
            setAnalysisError("");
            const data = await analyzeQuizResult(result.id);
            setAnalysis(data);
        } catch (error) {
            setAnalysisError(error.message || "Analiz yüklenirken hata oluştu.");
        } finally {
            setLoadingAnalysis(false);
        }
    }

    const [isAdapted, setIsAdapted] = useState(result.is_adapted || false);
    const [adapting, setAdapting] = useState(false);
    const [adaptSuccess, setAdaptSuccess] = useState("");
    const [adaptError, setAdaptError] = useState("");

    async function handleAdaptCurriculum() {
        if (!result.id || !result.plan_id) return;
        try {
            setAdapting(true);
            setAdaptError("");
            setAdaptSuccess("");
            await adaptPlanFromQuiz(result.plan_id, result.id);
            setIsAdapted(true);
            setAdaptSuccess("Müfredat zayıf konularına göre uyarlandı! Bir sonraki haftaya tekrar görevleri eklendi.");
        } catch (error) {
            setAdaptError(error.message || "Müfredat uyarlanırken hata oluştu.");
        } finally {
            setAdapting(false);
        }
    }

    return (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl shadow-slate-950/30">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                <div>
                    <p className="text-sm font-semibold text-indigo-300">
                        Plan ID: {result.plan_id} | Hafta ID: {result.week_id}
                    </p>

                    <h3 className="mt-2 text-2xl font-bold text-slate-50">
                        {result.quiz_title}
                    </h3>

                    <p className="mt-2 text-sm text-slate-500">
                        {result.created_at?.slice(0, 19).replace("T", " ")}
                    </p>
                </div>

                <div className="rounded-2xl bg-slate-950/60 px-5 py-4">
                    <p className="text-xs text-slate-500">
                        Skor
                    </p>

                    <p className="mt-1 text-2xl font-bold text-slate-100">
                        {result.correct_count}/{result.total_questions}
                    </p>

                    <p className="mt-1 text-sm text-slate-400">
                        %{score}
                    </p>
                </div>
            </div>

            <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-800">
                <div
                    className="h-full rounded-full bg-emerald-500"
                    style={{ width: `${score}%` }}
                />
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
            {score < 100 && result.id && (
                <div className="mt-5 pt-5 border-t border-slate-800/60">
                    {!analysis && (
                        <button
                            type="button"
                            onClick={handleAnalyzeQuiz}
                            disabled={loadingAnalysis}
                            className="w-full rounded-2xl bg-gradient-to-r from-amber-500 to-orange-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-orange-500/20 transition hover:from-amber-400 hover:to-orange-500 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {loadingAnalysis ? "Zayıf Konular Analiz Ediliyor..." : "🔍 AI ile Zayıf Konuları Analiz Et"}
                        </button>
                    )}

                    {analysisError && (
                        <div className="mt-3 rounded-xl border border-red-900/60 bg-red-950/40 px-4 py-3 text-xs text-red-200">
                            {analysisError}
                        </div>
                    )}

                    {analysis && (
                        <div className="mt-4 rounded-2xl border border-indigo-500/20 bg-indigo-950/20 p-5">
                            <h6 className="text-md font-bold text-indigo-300 flex items-center gap-2">
                                💡 Yapay Zekâ Analiz Raporu
                            </h6>
                            
                            <p className="mt-2 text-sm text-slate-300 italic">
                                "{analysis.summary}"
                            </p>

                            {analysis.weak_topics && analysis.weak_topics.length > 0 && (
                                <div className="mt-4">
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Tespit Edilen Zayıf Konular</span>
                                    <div className="mt-2 flex flex-wrap gap-2">
                                        {analysis.weak_topics.map((topic, i) => (
                                            <span key={i} className="rounded-lg bg-red-500/10 border border-red-500/30 px-3 py-1 text-xs font-semibold text-red-200">
                                                ⚠️ {topic}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {analysis.recommended_actions && analysis.recommended_actions.length > 0 && (
                                <div className="mt-4">
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Gelişim Önerileri</span>
                                    <ul className="mt-2 space-y-1.5 text-sm text-slate-300 list-disc list-inside">
                                        {analysis.recommended_actions.map((action, i) => (
                                            <li key={i}>{action}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {analysis.recommended_resources && analysis.recommended_resources.length > 0 && (
                                <div className="mt-4 pt-4 border-t border-slate-800">
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Önerilen Arama Terimleri / Kaynaklar</span>
                                    <ul className="mt-2 space-y-1.5 text-sm text-indigo-200">
                                        {analysis.recommended_resources.map((resItem, i) => (
                                            <li key={i} className="flex items-start gap-2">
                                                <span>🔍</span>
                                                <span>{resItem}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Müfredat Uyumlama Butonu */}
                            <div className="mt-5 pt-4 border-t border-slate-800/80">
                                {isAdapted ? (
                                    <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 p-3 text-xs font-semibold text-emerald-300">
                                        <span>✓ Müfredat bu analize göre uyarlandı (Zayıf konu tekrar görevleri eklendi).</span>
                                    </div>
                                ) : (
                                    <>
                                        <button
                                            type="button"
                                            onClick={handleAdaptCurriculum}
                                            disabled={adapting}
                                            className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-4 py-2.5 text-xs font-bold text-white shadow-md shadow-indigo-500/10 transition hover:from-indigo-400 hover:to-purple-500 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            {adapting ? "Müfredat Güncelleniyor..." : "🔄 Müfredatı Zayıf Konulara Göre Güncelle"}
                                        </button>
                                        
                                        {adaptError && (
                                            <div className="mt-2 text-xs text-red-400">
                                                {adaptError}
                                            </div>
                                        )}
                                        {adaptSuccess && (
                                            <div className="mt-2 text-xs text-emerald-400 font-medium">
                                                {adaptSuccess}
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}
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
                        Soru {item.question_number}: {item.is_correct ? "Doğru" : "Yanlış"}
                    </p>

                    <p className="mt-3 text-sm font-semibold text-slate-100">
                        {item.question}
                    </p>

                    <p className="mt-3 text-sm text-slate-400">
                        <strong>Senin cevabın:</strong> {item.selected_answer || "Boş"}
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

export default QuizResultsPage;