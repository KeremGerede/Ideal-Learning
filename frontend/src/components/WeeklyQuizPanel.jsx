// src/components/WeeklyQuizPanel.jsx

import { useState } from "react";
import { generateWeeklyQuiz, saveQuizResult } from "../api/apiClient";

function WeeklyQuizPanel({ planId, week, onQuizSaved }) {
    /**
     * Haftalık quiz paneli.
     *
     * Bu component:
     * - Seçilen hafta için quiz oluşturur
     * - Kullanıcı cevaplarını tutar
     * - Skoru hesaplar
     * - Quiz sonucunu ve soru/cevap detaylarını backend'e kaydeder
     */

    const [quiz, setQuiz] = useState(null);
    const [selectedAnswers, setSelectedAnswers] = useState({});
    const [quizResult, setQuizResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [savingResult, setSavingResult] = useState(false);
    const [errorMessage, setErrorMessage] = useState("");
    const [successMessage, setSuccessMessage] = useState("");

    async function handleGenerateQuiz() {
        /**
         * Backend'den haftalık quiz üretir.
         * Yeni quiz oluşturulduğunda eski cevapları ve sonucu temizliyoruz.
         */

        try {
            setLoading(true);
            setErrorMessage("");
            setSuccessMessage("");
            setSelectedAnswers({});
            setQuizResult(null);

            const quizData = await generateWeeklyQuiz(planId, week.id);

            setQuiz(quizData);
        } catch (error) {
            setErrorMessage(error.message || "Quiz oluşturulurken hata oluştu.");
        } finally {
            setLoading(false);
        }
    }

    function handleAnswerChange(questionIndex, answer) {
        /**
         * Kullanıcının seçtiği cevabı questionIndex'e göre saklar.
         */

        setSelectedAnswers((previousAnswers) => ({
            ...previousAnswers,
            [questionIndex]: answer,
        }));
    }

    async function handleFinishQuiz() {
        /**
         * Kullanıcının cevaplarını kontrol eder, skoru hesaplar
         * ve sonucu backend'e kaydeder.
         */

        if (!quiz || !quiz.questions || quiz.questions.length === 0) {
            setErrorMessage("Hesaplanacak quiz bulunamadı.");
            return;
        }

        const questions = quiz.questions;
        const totalQuestions = questions.length;

        let correctCount = 0;
        const detailedResults = [];

        questions.forEach((question, index) => {
            const questionNumber = index + 1;
            const selectedAnswer = selectedAnswers[questionNumber] || null;
            const correctAnswer = question.correct_answer;
            const isCorrect = selectedAnswer === correctAnswer;

            if (isCorrect) {
                correctCount += 1;
            }

            detailedResults.push({
                question_number: questionNumber,
                question: question.question,
                selected_answer: selectedAnswer,
                correct_answer: correctAnswer,
                is_correct: isCorrect,
                explanation: question.explanation,
            });
        });

        const scorePercentage =
            totalQuestions === 0
                ? 0
                : Math.round((correctCount / totalQuestions) * 10000) / 100;

        const result = {
            correct_count: correctCount,
            total_questions: totalQuestions,
            score_percentage: scorePercentage,
            detailed_results: detailedResults,
        };

        setQuizResult(result);

        try {
            setSavingResult(true);
            setErrorMessage("");
            setSuccessMessage("");

            await saveQuizResult({
                plan_id: planId,
                week_id: week.id,
                quiz_title: quiz.quiz_title || `${week.title} Quiz`,
                correct_count: correctCount,
                total_questions: totalQuestions,

                // Backend details_json alanını string olarak bekliyor.
                details_json: JSON.stringify(detailedResults),
            });

            setSuccessMessage("Quiz sonucu başarıyla kaydedildi.");

            // Üst component'e haber veriyoruz.
            // Böylece PlanDetailPage kayıtlı quiz sonuçlarını tekrar yükleyebilir.
            if (onQuizSaved) {
                onQuizSaved();
            }
        } catch (error) {
            setErrorMessage(error.message || "Quiz sonucu kaydedilemedi.");
        } finally {
            setSavingResult(false);
        }
    }

    return (
        <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-950/50 p-5">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                    <h5 className="font-bold text-slate-100">
                        Haftalık Quiz
                    </h5>

                    <p className="mt-1 text-sm text-slate-500">
                        Bu haftadaki konuları ölçmek için AI destekli quiz oluştur.
                    </p>
                </div>

                <button
                    type="button"
                    onClick={handleGenerateQuiz}
                    disabled={loading}
                    className="rounded-2xl bg-indigo-500 px-4 py-2 text-sm font-bold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
                >
                    {loading ? "Quiz oluşturuluyor..." : "Quiz Oluştur"}
                </button>
            </div>

            {errorMessage && (
                <div className="mt-4 rounded-2xl border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                    {errorMessage}
                </div>
            )}

            {successMessage && (
                <div className="mt-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm font-semibold text-emerald-200">
                    {successMessage}
                </div>
            )}

            {quiz && (
                <div className="mt-6 space-y-5">
                    <div>
                        <h6 className="text-lg font-bold text-slate-100">
                            {quiz.quiz_title}
                        </h6>

                        <p className="mt-1 text-sm text-slate-500">
                            Soruları cevapladıktan sonra skoru hesaplayabilirsin.
                        </p>
                    </div>

                    {quiz.questions?.map((question, index) => {
                        const questionNumber = index + 1;

                        return (
                            <div
                                key={questionNumber}
                                className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5"
                            >
                                <p className="font-bold text-slate-100">
                                    Soru {questionNumber}: {question.question}
                                </p>

                                <div className="mt-4 space-y-3">
                                    {question.options?.map((option) => (
                                        <label
                                            key={option}
                                            className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-300 transition hover:border-indigo-500/50"
                                        >
                                            <input
                                                type="radio"
                                                name={`week-${week.id}-question-${questionNumber}`}
                                                value={option}
                                                checked={selectedAnswers[questionNumber] === option}
                                                onChange={() =>
                                                    handleAnswerChange(questionNumber, option)
                                                }
                                                className="accent-indigo-500"
                                            />

                                            <span>{option}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>
                        );
                    })}

                    <button
                        type="button"
                        onClick={handleFinishQuiz}
                        disabled={savingResult}
                        className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 px-5 py-3 text-sm font-bold text-emerald-200 transition hover:bg-emerald-500 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {savingResult ? "Sonuç kaydediliyor..." : "Quizi Bitir ve Skoru Hesapla"}
                    </button>
                </div>
            )}

            {quizResult && (
                <div className="mt-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-5">
                    <p className="text-sm font-semibold text-emerald-200">
                        Quiz Sonucu
                    </p>

                    <h6 className="mt-2 text-2xl font-bold text-slate-50">
                        {quizResult.correct_count}/{quizResult.total_questions} doğru - %
                        {quizResult.score_percentage}
                    </h6>

                    <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-800">
                        <div
                            className="h-full rounded-full bg-emerald-500"
                            style={{ width: `${quizResult.score_percentage}%` }}
                        />
                    </div>

                    <details className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
                        <summary className="cursor-pointer text-sm font-semibold text-emerald-200">
                            Cevap detaylarını göster
                        </summary>

                        <div className="mt-4 space-y-3">
                            {quizResult.detailed_results.map((item) => (
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
                    </details>
                </div>
            )}
        </div>
    );
}

export default WeeklyQuizPanel;