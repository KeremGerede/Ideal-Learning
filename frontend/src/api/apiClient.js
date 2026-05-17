// src/api/apiClient.js

// FastAPI backend adresi.
// Backend şu anda 8000 portunda çalışıyor.
const API_BASE_URL = "http://127.0.0.1:8000";

export async function getHealthStatus() {
    /**
     * Backend'in çalışıp çalışmadığını kontrol eder.
     * FastAPI endpoint: GET /health
     */

    const response = await fetch(`${API_BASE_URL}/health`);

    if (!response.ok) {
        throw new Error("Backend health check başarısız oldu.");
    }

    return response.json();
}

export async function getStatsOverview() {
    /**
     * Dashboard için genel istatistikleri backend'den alır.
     * FastAPI endpoint: GET /stats/overview
     */

    const response = await fetch(`${API_BASE_URL}/stats/overview`);

    if (!response.ok) {
        throw new Error("Dashboard istatistikleri alınamadı.");
    }

    return response.json();
}

export async function generatePlan(planPayload) {
    /**
     * Kullanıcının formdan girdiği bilgilerle yeni öğrenme planı oluşturur.
     * FastAPI endpoint: POST /plans/generate
     */

    const response = await fetch(`${API_BASE_URL}/plans/generate`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(planPayload),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Plan oluşturulamadı.");
    }

    return response.json();
}


export async function getAllPlans() {
    /**
     * Veritabanındaki tüm öğrenme planlarını getirir.
     * FastAPI endpoint: GET /plans
     */

    const response = await fetch(`${API_BASE_URL}/plans`);

    if (!response.ok) {
        throw new Error("Planlar alınamadı.");
    }

    return response.json();
}

export async function deletePlanById(planId) {
    /**
     * Seçilen öğrenme planını siler.
     * FastAPI endpoint: DELETE /plans/{plan_id}
     */

    const response = await fetch(`${API_BASE_URL}/plans/${planId}`, {
        method: "DELETE",
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Plan silinemedi.");
    }

    return response.json();
}

export async function getPlanById(planId) {
    /**
     * Seçilen öğrenme planının detaylarını getirir.
     * FastAPI endpoint: GET /plans/{plan_id}
     */

    const response = await fetch(`${API_BASE_URL}/plans/${planId}`);

    if (!response.ok) {
        throw new Error("Plan detayı alınamadı.");
    }

    return response.json();
}

export async function updateTaskCompletion(taskId, isCompleted) {
    /**
     * Görevin tamamlanma durumunu günceller.
     * FastAPI endpoint: PATCH /tasks/{task_id}/complete?is_completed=true
     */

    const response = await fetch(
        `${API_BASE_URL}/tasks/${taskId}/complete?is_completed=${isCompleted}`,
        {
            method: "PATCH",
        }
    );

    if (!response.ok) {
        throw new Error("Görev durumu güncellenemedi.");
    }

    return response.json();
}

export async function getQuizResultsByPlan(planId) {
    /**
     * Seçilen plana ait kayıtlı quiz sonuçlarını getirir.
     * FastAPI endpoint: GET /quiz-results/plan/{plan_id}
     */

    const response = await fetch(`${API_BASE_URL}/quiz-results/plan/${planId}`);

    if (!response.ok) {
        throw new Error("Quiz sonuçları alınamadı.");
    }

    return response.json();
}




export async function generateWeeklyQuiz(planId, weekId) {
    /**
     * Seçilen planın seçilen haftası için AI destekli quiz üretir.
     * FastAPI endpoint: POST /quiz/plans/{plan_id}/weeks/{week_id}/generate
     */

    const response = await fetch(
        `${API_BASE_URL}/quiz/plans/${planId}/weeks/${weekId}/generate`,
        {
            method: "POST",
        }
    );

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Quiz oluşturulamadı.");
    }

    return response.json();
}

export async function saveQuizResult(resultPayload) {
    /**
     * Çözülen quiz sonucunu backend'e kaydeder.
     * FastAPI endpoint: POST /quiz-results/
     *
     * resultPayload içinde:
     * - plan_id
     * - week_id
     * - quiz_title
     * - correct_count
     * - total_questions
     * - details_json
     * bulunur.
     */

    const response = await fetch(`${API_BASE_URL}/quiz-results/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(resultPayload),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Quiz sonucu kaydedilemedi.");
    }

    return response.json();
}


export async function getAllQuizResults() {
    /**
     * Sistemde kayıtlı tüm quiz sonuçlarını getirir.
     * FastAPI endpoint: GET /quiz-results/
     */

    const response = await fetch(`${API_BASE_URL}/quiz-results/`);

    if (!response.ok) {
        throw new Error("Quiz sonuçları alınamadı.");
    }

    return response.json();
}

export async function regeneratePlanWeek(planId, weekId, userInstruction) {
    const response = await fetch(
        `${API_BASE_URL}/plans/${planId}/weeks/${weekId}/regenerate`,
        {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                user_instruction: userInstruction,
            }),
        }
    );

    if (!response.ok) {
        throw new Error("Hafta AI ile yeniden oluşturulamadı.");
    }

    return response.json();
}