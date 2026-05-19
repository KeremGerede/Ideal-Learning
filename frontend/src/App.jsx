// src/App.jsx

import { useState } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Sidebar from "./components/Sidebar";
import DashboardPage from "./pages/DashboardPage";
import PlanCreatorPage from "./pages/PlanCreatorPage";
import MyPlansPage from "./pages/MyPlansPage";
import PlanDetailPage from "./pages/PlanDetailPage";
import QuizResultsPage from "./pages/QuizResultsPage";
import ResourcesPage from "./pages/ResourcesPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import MobileNavigation from "./components/MobileNavigation";

/**
 * Inner component that has access to AuthContext.
 * Renders auth pages when unauthenticated, full layout when authenticated.
 */
function AppContent() {
    const { isAuthenticated } = useAuth();

    const [activePage, setActivePage] = useState("dashboard");
    const [selectedPlanId, setSelectedPlanId] = useState(null);
    const [authPage, setAuthPage] = useState("login"); // "login" | "register"

    // ============================================================
    // AUTH GATE
    // ============================================================

    if (!isAuthenticated) {
        if (authPage === "register") {
            return (
                <RegisterPage
                    onSwitchToLogin={() => setAuthPage("login")}
                />
            );
        }

        return (
            <LoginPage
                onSwitchToRegister={() => setAuthPage("register")}
            />
        );
    }

    // ============================================================
    // PAGE NAVIGATION
    // ============================================================

    function handleViewPlanDetail(planId) {
        setSelectedPlanId(planId);
        setActivePage("plan-detail");
    }

    function handleBackToPlans() {
        setSelectedPlanId(null);
        setActivePage("my-plans");
    }

    function renderActivePage() {
        if (activePage === "plan-detail" && selectedPlanId) {
            return (
                <PlanDetailPage
                    planId={selectedPlanId}
                    onBack={handleBackToPlans}
                />
            );
        }

        if (activePage === "plan-create") {
            return (
                <PlanCreatorPage
                    onViewCreatedPlan={handleViewPlanDetail}
                />
            );
        }

        if (activePage === "my-plans") {
            return (
                <MyPlansPage
                    onViewPlanDetail={handleViewPlanDetail}
                />
            );
        }

        if (activePage === "quiz-results") {
            return <QuizResultsPage />;
        }

        if (activePage === "resources") {
            return <ResourcesPage />;
        }

        return <DashboardPage />;
    }

    // ============================================================
    // AUTHENTICATED LAYOUT
    // ============================================================

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100">
            <div className="flex">
                <Sidebar
                    activePage={activePage}
                    onPageChange={setActivePage}
                />

                <main className="min-h-screen flex-1 px-5 py-6 md:px-8 lg:px-10">
                    <MobileNavigation
                        activePage={activePage}
                        onPageChange={setActivePage}
                    />

                    {renderActivePage()}
                </main>
            </div>
        </div>
    );
}

function App() {
    return (
        <AuthProvider>
            <AppContent />
        </AuthProvider>
    );
}

export default App;
