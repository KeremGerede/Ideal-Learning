// src/App.jsx

import { useState } from "react";
import Sidebar from "./components/Sidebar";
import DashboardPage from "./pages/DashboardPage";
import PlanCreatorPage from "./pages/PlanCreatorPage";
import MyPlansPage from "./pages/MyPlansPage";
import PlanDetailPage from "./pages/PlanDetailPage";
import QuizResultsPage from "./pages/QuizResultsPage";
import ResourcesPage from "./pages/ResourcesPage";
import MobileNavigation from "./components/MobileNavigation";

function App() {
  /**
   * Uygulamanın ana layout componenti.
   *
   * Şimdilik react-router kullanmadan basit page state ile ilerliyoruz.
   */

  const [activePage, setActivePage] = useState("dashboard");
  const [selectedPlanId, setSelectedPlanId] = useState(null);


  function handleViewPlanDetail(planId) {
    /**
     * Planlarım sayfasındaki Detayı Gör butonundan gelir.
     * Seçilen plan ID'sini saklar ve detay sayfasını açar.
     */

    setSelectedPlanId(planId);
    setActivePage("plan-detail");
  }

  function handleBackToPlans() {
    /**
     * Plan detayından plan listesine geri döner.
     */

    setSelectedPlanId(null);
    setActivePage("my-plans");
  }


  function renderActivePage() {
    /**
     * Sidebar'dan seçilen menüye göre ilgili sayfayı render eder.
     */

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

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="flex">
        <Sidebar
          activePage={activePage}
          onPageChange={setActivePage}
        />

        <main className="min-h-screen flex-1 px-5 py-6 md:px-8 lg:px-10">
          {/* Küçük ekranlarda sidebar gizlendiği için mobil navigasyon gösteriyoruz. */}
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

export default App;