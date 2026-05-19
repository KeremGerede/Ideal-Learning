// src/api/apiClient.js

const API_BASE_URL = "http://127.0.0.1:8000";

// ================================================================
// AUTH HELPERS
// ================================================================

function getAuthToken() {
    return localStorage.getItem("auth_token");
}

function authHeaders() {
    const token = getAuthToken();
    return token
        ? { "Authorization": `Bearer ${token}` }
        : {};
}

/**
 * Generic fetch wrapper that attaches auth headers and handles
 * 401 responses by clearing local auth state and reloading.
 */
async function apiFetch(url, options = {}) {
    const headers = {
        ...authHeaders(),
        ...(options.headers || {}),
    };

    const response = await fetch(url, { ...options, headers });

    if (response.status === 401) {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
        window.location.reload();
        // Throw to stop further execution while the page reloads.
        throw new Error("Oturum süresi doldu. Lütfen tekrar giriş yapın.");
    }

    return response;
}

// ================================================================
// AUTH ENDPOINTS
// ================================================================

export async function loginUser(payload) {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Giriş yapılamadı.");
    }

    return response.json();
}

export async function registerUser(payload) {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Kayıt oluşturulamadı.");
    }

    return response.json();
}

export async function getMe(token) {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: { "Authorization": `Bearer ${token}` },
    });

    if (!response.ok) {
        throw new Error("Kullanıcı bilgileri alınamadı.");
    }

    return response.json();
}

// ================================================================
// HEALTH
// ================================================================

export async function getHealthStatus() {
    const response = await fetch(`${API_BASE_URL}/health`);

    if (!response.ok) {
        throw new Error("Backend health check başarısız oldu.");
    }

    return response.json();
}

// ================================================================
// STATS
// ================================================================

export async function getStatsOverview() {
    const response = await apiFetch(`${API_BASE_URL}/stats/overview`);

    if (!response.ok) {
        throw new Error("Dashboard istatistikleri alınamadı.");
    }

    return response.json();
}

// ================================================================
// PLANS
// ================================================================

export async function generatePlan(planPayload) {
    const response = await apiFetch(`${API_BASE_URL}/plans/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(planPayload),
    });

    if (!response.ok) {
        const errorText = await response.text();
        // Try to extract the detail field from JSON error body.
        try {
            const parsed = JSON.parse(errorText);
            throw new Error(parsed.detail || errorText);
        } catch (parseError) {
            if (parseError.message !== errorText) throw parseError;
            throw new Error(errorText || "Plan oluşturulamadı.");
        }
    }

    return response.json();
}

export async function getAllPlans() {
    const response = await apiFetch(`${API_BASE_URL}/plans`);

    if (!response.ok) {
        throw new Error("Planlar alınamadı.");
    }

    return response.json();
}

export async function deletePlanById(planId) {
    const response = await apiFetch(`${API_BASE_URL}/plans/${planId}`, {
        method: "DELETE",
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Plan silinemedi.");
    }

    return response.json();
}

export async function getPlanById(planId) {
    const response = await apiFetch(`${API_BASE_URL}/plans/${planId}`);

    if (!response.ok) {
        throw new Error("Plan detayı alınamadı.");
    }

    return response.json();
}

// ================================================================
// TASKS
// ================================================================

export async function updateTaskCompletion(taskId, isCompleted) {
    const response = await apiFetch(
        `${API_BASE_URL}/tasks/${taskId}/complete?is_completed=${isCompleted}`,
        { method: "PATCH" }
    );

    if (!response.ok) {
        throw new Error("Görev durumu güncellenemedi.");
    }

    return response.json();
}

// ================================================================
// QUIZ
// ================================================================

export async function generateWeeklyQuiz(planId, weekId) {
    const response = await apiFetch(
        `${API_BASE_URL}/quiz/plans/${planId}/weeks/${weekId}/generate`,
        { method: "POST" }
    );

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Quiz oluşturulamadı.");
    }

    return response.json();
}

// ================================================================
// QUIZ RESULTS
// ================================================================

export async function saveQuizResult(resultPayload) {
    const response = await apiFetch(`${API_BASE_URL}/quiz-results/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(resultPayload),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Quiz sonucu kaydedilemedi.");
    }

    return response.json();
}

export async function getQuizResultsByPlan(planId) {
    const response = await apiFetch(`${API_BASE_URL}/quiz-results/plan/${planId}`);

    if (!response.ok) {
        throw new Error("Quiz sonuçları alınamadı.");
    }

    return response.json();
}

export async function getAllQuizResults() {
    const response = await apiFetch(`${API_BASE_URL}/quiz-results/`);

    if (!response.ok) {
        throw new Error("Quiz sonuçları alınamadı.");
    }

    return response.json();
}

// ================================================================
// WEEK REGENERATION
// ================================================================

export async function regeneratePlanWeek(planId, weekId, userInstruction) {
    const response = await apiFetch(
        `${API_BASE_URL}/plans/${planId}/weeks/${weekId}/regenerate`,
        {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_instruction: userInstruction }),
        }
    );

    if (!response.ok) {
        throw new Error("Hafta AI ile yeniden oluşturulamadı.");
    }

    return response.json();
}

// ================================================================
// RECOMMENDATIONS
// ================================================================

export async function getLearningRecommendations(limit = 6) {
    const response = await apiFetch(
        `${API_BASE_URL}/recommendations/?limit=${limit}`
    );

    if (!response.ok) {
        throw new Error("Öğrenme önerileri alınamadı.");
    }

    return response.json();
}
