import json
import requests
import streamlit as st


# ============================================================
# API CONFIG
# ============================================================
# FastAPI backend'in çalıştığı adres.
# Backend'i şu komutla çalıştırıyoruz:
# uvicorn app.main:app --reload
API_BASE_URL = "http://127.0.0.1:8000"


# ============================================================
# PAGE CONFIG
# ============================================================
# Streamlit sayfa başlığı, ikon ve genişlik ayarları.
st.set_page_config(
    page_title="AI Learning Planner",
    page_icon="🎓",
    layout="wide"
)


# ============================================================
# SESSION STATE
# ============================================================
# Streamlit her butona/checkbox'a basıldığında dosyayı baştan çalıştırır.
# Bu yüzden açık olan planı kaybetmemek için active_plan_id değerini session_state içinde tutuyoruz.
if "active_plan_id" not in st.session_state:
    st.session_state.active_plan_id = None

if "last_created_plan_id" not in st.session_state:
    st.session_state.last_created_plan_id = None

if "success_message" not in st.session_state:
    st.session_state.success_message = None

if "generated_quizzes" not in st.session_state:
    st.session_state.generated_quizzes = {}


# ============================================================
# API HELPER FUNCTIONS
# ============================================================

def generate_plan(payload: dict):
    """
    Kullanıcı formundan gelen bilgilerle yeni öğrenme planı oluşturur.

    FastAPI endpoint:
    POST /plans/generate
    """

    try:
        response = requests.post(
            f"{API_BASE_URL}/plans/generate",
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            return response.json(), None

        return None, response.text

    except requests.exceptions.ConnectionError:
        return None, "FastAPI backend çalışmıyor."

    except Exception as e:
        return None, str(e)


def get_all_plans():
    """
    Veritabanındaki tüm öğrenme planlarını backend'den alır.

    FastAPI endpoint:
    GET /plans
    """

    try:
        response = requests.get(
            f"{API_BASE_URL}/plans",
            timeout=30
        )

        if response.status_code == 200:
            return response.json()

        return None

    except requests.exceptions.ConnectionError:
        return None

    except Exception:
        return None


def get_plan_by_id(plan_id: int):
    """
    Belirli bir planın detaylarını backend'den alır.

    FastAPI endpoint:
    GET /plans/{plan_id}
    """

    try:
        response = requests.get(
            f"{API_BASE_URL}/plans/{plan_id}",
            timeout=30
        )

        if response.status_code == 200:
            return response.json()

        return None

    except requests.exceptions.ConnectionError:
        return None

    except Exception:
        return None


def delete_plan_by_id(plan_id: int):
    """
    Belirli bir öğrenme planını backend üzerinden siler.

    FastAPI endpoint:
    DELETE /plans/{plan_id}
    """

    try:
        response = requests.delete(
            f"{API_BASE_URL}/plans/{plan_id}",
            timeout=30
        )

        if response.status_code == 200:
            return True, None

        return False, response.text

    except requests.exceptions.ConnectionError:
        return False, "FastAPI backend çalışmıyor. Plan silinemedi."

    except Exception as e:
        return False, str(e)


def get_plan_progress(plan_id: int):
    """
    Belirli bir öğrenme planının ilerleme yüzdesini backend'den alır.

    FastAPI endpoint:
    GET /plans/{plan_id}/progress
    """

    try:
        response = requests.get(
            f"{API_BASE_URL}/plans/{plan_id}/progress",
            timeout=30
        )

        if response.status_code == 200:
            return response.json()

        return None

    except requests.exceptions.ConnectionError:
        return None

    except Exception:
        return None


def get_stats_overview():
    """
    Genel dashboard istatistiklerini backend'den alır.

    FastAPI endpoint:
    GET /stats/overview
    """

    try:
        response = requests.get(
            f"{API_BASE_URL}/stats/overview",
            timeout=30
        )

        if response.status_code == 200:
            return response.json()

        return None

    except requests.exceptions.ConnectionError:
        return None

    except Exception:
        return None


def update_task_completion(task_id: int, is_completed: bool):
    """
    Bir görevin tamamlandı/tamamlanmadı durumunu backend'e gönderir.

    FastAPI endpoint:
    PATCH /tasks/{task_id}/complete?is_completed=true
    """

    try:
        response = requests.patch(
            f"{API_BASE_URL}/tasks/{task_id}/complete",
            params={"is_completed": is_completed},
            timeout=30
        )

        if response.status_code == 200:
            return True, None

        return False, response.text

    except requests.exceptions.ConnectionError:
        return False, "FastAPI backend çalışmıyor. Görev güncellenemedi."

    except Exception as e:
        return False, str(e)

# QUIZ GENERATION FUNCTION
def generate_weekly_quiz(plan_id: int, week_id: int):
    """
    Belirli bir planın belirli haftası için quiz üretir.

    FastAPI endpoint:
    POST /quiz/plans/{plan_id}/weeks/{week_id}/generate
    """

    try:
        response = requests.post(
            f"{API_BASE_URL}/quiz/plans/{plan_id}/weeks/{week_id}/generate",
            timeout=60
        )

        if response.status_code == 200:
            return response.json(), None

        return None, response.text

    except requests.exceptions.ConnectionError:
        return None, "FastAPI backend çalışmıyor. Quiz üretilemedi."

    except Exception as e:
        return None, str(e)



def save_quiz_result(
    plan_id: int,
    week_id: int,
    quiz_title: str,
    correct_count: int,
    total_questions: int,
    detailed_results: list | None = None
):
    """
    Quiz sonucunu backend üzerinden veritabanına kaydeder.

    FastAPI endpoint:
    POST /quiz-results/

    Not:
    - correct_count ve total_questions skor hesaplama için kullanılır.
    - detailed_results ise soru/cevap detaylarını JSON olarak saklamak için gönderilir.
    """

    payload = {
        "plan_id": plan_id,
        "week_id": week_id,
        "quiz_title": quiz_title,
        "correct_count": correct_count,
        "total_questions": total_questions,
        "details_json": json.dumps(
            detailed_results or [],
            ensure_ascii=False
        )
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/quiz-results/",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            return response.json(), None

        return None, response.text

    except requests.exceptions.ConnectionError:
        return None, "FastAPI backend çalışmıyor. Quiz sonucu kaydedilemedi."

    except Exception as e:
        return None, str(e)

def get_quiz_results_by_plan(plan_id: int):
    """
    Belirli bir plana ait kayıtlı quiz sonuçlarını backend'den alır.

    FastAPI endpoint:
    GET /quiz-results/plan/{plan_id}
    """

    try:
        response = requests.get(
            f"{API_BASE_URL}/quiz-results/plan/{plan_id}",
            timeout=30
        )

        if response.status_code == 200:
            return response.json()

        return []

    except requests.exceptions.ConnectionError:
        return []

    except Exception:
        return []


# ============================================================
# UI RENDER FUNCTIONS
# ============================================================

def render_dashboard_overview():
    """
    Ana sayfada genel sistem istatistiklerini kartlar halinde gösterir.

    Gösterilen metrikler:
    - Toplam plan
    - Toplam görev
    - Tamamlanan görev
    - Genel ilerleme
    - Toplam quiz
    - Ortalama quiz başarısı
    - En son quiz skoru
    """

    stats = get_stats_overview()

    if not stats:
        st.info("Dashboard istatistikleri alınamadı.")
        return

    st.subheader("📊 Genel Durum")

    # Birinci satır: plan ve görev metrikleri
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Toplam Plan", stats["total_plans"])

    with col2:
        st.metric("Toplam Görev", stats["total_tasks"])

    with col3:
        st.metric("Tamamlanan Görev", stats["completed_tasks"])

    with col4:
        st.metric(
            "Genel İlerleme",
            f'%{stats["overall_progress_percentage"]}'
        )

    st.progress(stats["overall_progress_percentage"] / 100)

    st.divider()

    # İkinci satır: quiz metrikleri
    quiz_col1, quiz_col2, quiz_col3 = st.columns(3)

    with quiz_col1:
        st.metric(
            "Toplam Quiz",
            stats.get("total_quizzes", 0)
        )

    with quiz_col2:
        st.metric(
            "Ortalama Quiz Başarısı",
            f'%{stats.get("average_quiz_score", 0)}'
        )

    with quiz_col3:
        latest_score = stats.get("latest_quiz_score")

        if latest_score is None:
            latest_score_text = "Yok"
        else:
            latest_score_text = f"%{latest_score}"

        st.metric(
            "En Son Quiz Skoru",
            latest_score_text
        )

def render_progress(plan_id: int):
    """
    Plan için progress bar ve görev tamamlanma bilgisini ekrana basar.
    """

    progress = get_plan_progress(plan_id)

    if not progress:
        st.info("İlerleme bilgisi alınamadı.")
        return

    st.subheader("📈 İlerleme Durumu")

    progress_value = progress["progress_percentage"] / 100
    st.progress(progress_value)

    st.write(
        f'Tamamlanan görev: **{progress["completed_tasks"]}** / '
        f'**{progress["total_tasks"]}**'
    )

    st.write(f'İlerleme yüzdesi: **%{progress["progress_percentage"]}**')


def render_plan_detail(plan: dict):
    """
    Aktif öğrenme planının detaylarını gösterir.
    Haftalar, görevler, kaynaklar ve ilerleme durumu burada render edilir.
    """

    st.markdown("### 📌 Plan Özeti")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Konu", plan["topic"])

    with col2:
        st.metric("Seviye", plan["level"])

    with col3:
        st.metric("Haftalık Saat", plan["weekly_hours"])

    with col4:
        st.metric("Süre", f'{plan["duration_weeks"]} hafta')

    st.write("**Hedef:**", plan["goal"])
    st.write("**Öğrenme Tercihi:**", plan.get("learning_preference"))

    # AI tarafından oluşturulan genel plan özetini gösterir.
    if plan.get("summary"):
        st.info(f'📝 Plan Özeti: {plan["summary"]}')

    # Plan tamamlandığında kullanıcının kazanacağı beceriyi gösterir.
    if plan.get("final_outcome"):
        st.success(f'🎯 Plan Sonu Kazanım: {plan["final_outcome"]}')

    # Planın güncel ilerleme yüzdesini gösterir.
    render_progress(plan["id"])

    st.divider()

    # Daha önce tamamlanıp veritabanına kaydedilen quiz sonuçlarını gösteriyoruz.
    render_saved_quiz_results(plan["id"])

    st.divider()

    st.markdown("### 🗓️ Haftalık Öğrenme Planı")

    # Haftalık planları gösteriyoruz.
    for week in plan.get("weeks", []):
        with st.expander(
            f'Hafta {week["week_number"]}: {week["title"]}',
            expanded=True
        ):
            if week.get("description"):
                st.write(week["description"])

            # Haftanın tahmini çalışma süresini gösterir.
            if week.get("estimated_hours"):
                st.caption(f'⏱️ Tahmini çalışma süresi: {week["estimated_hours"]} saat')

            # Haftalık mini proje önerisini görevlerden ayrı gösterir.
            if week.get("mini_project"):
                st.info(f'🧩 Mini Proje: {week["mini_project"]}')

            st.markdown("**Görevler:**")

            # Her görev checkbox olarak gösterilir.
            # Checkbox değişirse backend'e PATCH isteği gönderilir.
            for task in week.get("tasks", []):
                checkbox_key = f'plan_{plan["id"]}_task_{task["id"]}'

                # Göreve ait ek bilgileri küçük etiketler halinde hazırlıyoruz.
                task_meta = []

                if task.get("task_type"):
                    task_meta.append(f'📌 {task["task_type"]}')

                if task.get("estimated_minutes"):
                    task_meta.append(f'⏱️ {task["estimated_minutes"]} dk')

                if task.get("difficulty"):
                    task_meta.append(f'🎯 {task["difficulty"]}')

                if task_meta:
                    st.caption(" | ".join(task_meta))

                new_value = st.checkbox(
                    task["task_text"],
                    value=task["is_completed"],
                    key=checkbox_key
                )

                if new_value != task["is_completed"]:
                    success, error = update_task_completion(
                        task_id=task["id"],
                        is_completed=new_value
                    )

                    if success:
                        st.toast("Görev güncellendi.")
                        st.rerun()
                    else:
                        st.error("Görev güncellenemedi.")
                        st.code(error)

            resources = week.get("resources", [])

            if resources:
                st.markdown("**Kaynaklar:**")

                for resource in resources:
                    st.write(
                        f'- **{resource["resource_title"]}** '
                        f'({resource.get("resource_type") or "Kaynak"})'
                    )

                    if resource.get("resource_description"):
                        st.caption(resource["resource_description"])

                    if resource.get("resource_url"):
                        st.link_button(
                            "Kaynağı Aç",
                            resource["resource_url"]
                        )

            st.divider()

            st.markdown("**Haftalık Quiz:**")

            quiz_key = f'quiz_week_{week["id"]}'

            if st.button(
                "Quiz Oluştur",
                key=f'generate_quiz_{plan["id"]}_{week["id"]}'
            ):
                with st.spinner("Quiz oluşturuluyor..."):
                    quiz_data, error = generate_weekly_quiz(
                        plan_id=plan["id"],
                        week_id=week["id"]
                    )

                if quiz_data:
                    st.session_state.generated_quizzes[quiz_key] = quiz_data
                    st.success("Quiz başarıyla oluşturuldu.")
                    st.rerun()

                else:
                    st.error("Quiz oluşturulamadı.")
                    st.code(error)

            if quiz_key in st.session_state.generated_quizzes:
                quiz = st.session_state.generated_quizzes[quiz_key]

                st.write(f'### {quiz["quiz_title"]}')

                questions = quiz.get("questions", [])

                # Kullanıcının cevaplarını tutmak için dictionary.
                user_answers = {}

                for index, question in enumerate(questions, start=1):
                    with st.container(border=True):
                        st.write(f'**Soru {index}:** {question["question"]}')

                        selected_answer = st.radio(
                            "Cevabın:",
                            question["options"],
                            key=f'quiz_{week["id"]}_question_{index}'
                        )

                        user_answers[index] = selected_answer

                result_key = f'quiz_result_{week["id"]}'

                if st.button(
                    "Quizi Bitir ve Skoru Hesapla",
                    key=f'finish_quiz_{plan["id"]}_{week["id"]}'
                ):
                    # Kullanıcının doğru cevap sayısını hesaplamak için sayaç oluşturuyoruz.
                    # Bu değişken sadece butona basıldığında oluşmalı ve kullanılmalı.
                    correct_count = 0
                    detailed_results = []

                    # Her soruyu tek tek kontrol ediyoruz.
                    for index, question in enumerate(questions, start=1):
                        selected_answer = user_answers.get(index)
                        correct_answer = question["correct_answer"]
                        is_correct = selected_answer == correct_answer

                        if is_correct:
                            correct_count += 1

                        detailed_results.append({
                            "question_number": index,
                            "question": question["question"],
                            "selected_answer": selected_answer,
                            "correct_answer": correct_answer,
                            "is_correct": is_correct,
                            "explanation": question["explanation"]
                        })

                    total_questions = len(questions)

                    if total_questions == 0:
                        score_percentage = 0
                    else:
                        score_percentage = round(
                            (correct_count / total_questions) * 100,
                            2
                        )

                    # Quiz sonucunu önce Streamlit session_state içine kaydediyoruz.
                    # Böylece sayfa yeniden çizildiğinde sonuç ekranda gösterilebilir.
                    st.session_state[result_key] = {
                        "correct_count": correct_count,
                        "total_questions": total_questions,
                        "score_percentage": score_percentage,
                        "detailed_results": detailed_results
                    }

                    # Quiz sonucu hesaplandıktan sonra backend'e kaydediyoruz.
                    # Bu kod mutlaka correct_count hesaplandıktan sonra ve bu buton bloğunun içinde olmalı.
                    saved_result, save_error = save_quiz_result(
                        plan_id=plan["id"],
                        week_id=week["id"],
                        quiz_title=quiz["quiz_title"],
                        correct_count=correct_count,
                        total_questions=total_questions,
                        detailed_results=detailed_results
                    )

                    if saved_result:
                        st.session_state.success_message = "Quiz sonucu başarıyla kaydedildi."
                    else:
                        st.session_state.success_message = f"Quiz sonucu kaydedilemedi: {save_error}"

                    st.rerun()

                if result_key in st.session_state:
                    result = st.session_state[result_key]

                    st.success(
                        f'Quiz sonucu: {result["correct_count"]} / '
                        f'{result["total_questions"]} doğru'
                    )

                    st.progress(result["score_percentage"] / 100)

                    st.write(
                        f'Başarı oranı: **%{result["score_percentage"]}**'
                    )

                    with st.expander("Cevap Detaylarını Göster", expanded=False):
                        for item in result["detailed_results"]:
                            with st.container(border=True):
                                if item["is_correct"]:
                                    st.success(
                                        f'Soru {item["question_number"]}: Doğru'
                                    )
                                else:
                                    st.error(
                                        f'Soru {item["question_number"]}: Yanlış'
                                    )

                                st.write(f'**Soru:** {item["question"]}')
                                st.write(f'**Senin cevabın:** {item["selected_answer"]}')
                                st.write(f'**Doğru cevap:** {item["correct_answer"]}')
                                st.info(f'**Açıklama:** {item["explanation"]}')

    # Debug ve geliştirme için ham JSON çıktısı.
    # React frontend'e geçerken response yapısını anlamak için işe yarar.
    with st.expander("Ham JSON çıktısı"):
        st.json(plan)


def render_saved_plans():
    """
    Oluşturulan planları kartlar halinde listeler.
    Her kartta progress bar ve 'Detayları Aç' butonu bulunur.
    """

    st.subheader("📚 Oluşturulan Planlar")

    plans = get_all_plans()

    if plans is None:
        st.info("Planları görmek için FastAPI backend çalışıyor olmalı.")
        return

    if not plans:
        st.info("Henüz oluşturulmuş plan yok.")
        return

    for plan in plans:
        with st.container(border=True):
            st.write(f'### {plan["topic"]} - {plan["level"]}')

            st.write(f'**Hedef:** {plan["goal"]}')

            st.write(
                f'**Süre:** {plan["duration_weeks"]} hafta | '
                f'**Haftalık:** {plan["weekly_hours"]} saat'
            )

            progress = get_plan_progress(plan["id"])

            if progress:
                st.progress(progress["progress_percentage"] / 100)

                st.caption(
                    f'Tamamlanan görev: {progress["completed_tasks"]} / '
                    f'{progress["total_tasks"]} | '
                    f'%{progress["progress_percentage"]}'
                )

            st.caption(f'Plan ID: {plan["id"]}')

            # Bu buton planı yukarıda detaylı şekilde açmak için kullanılır.
            col_open, col_delete = st.columns([1, 1])

            with col_open:
                if st.button(
                    "Detayları Aç",
                    key=f'open_plan_{plan["id"]}'
                ):
                    st.session_state.active_plan_id = plan["id"]
                    st.rerun()

            with col_delete:
                if st.button(
                    "Sil",
                    key=f'delete_plan_{plan["id"]}'
                ):
                    success, error = delete_plan_by_id(plan["id"])

                    if success:
                        # Eğer silinen plan aktif plansa active_plan_id değerini temizliyoruz.
                        if st.session_state.active_plan_id == plan["id"]:
                            st.session_state.active_plan_id = None

                        st.session_state.success_message = "Plan başarıyla silindi."
                        st.rerun()

                    else:
                        st.error("Plan silinemedi.")
                        st.code(error)


def render_saved_quiz_results(plan_id: int):
    """
    Aktif öğrenme planına ait daha önce kaydedilmiş quiz sonuçlarını gösterir.

    Amaç:
    - Kullanıcı sayfayı yenilese bile geçmiş quiz skorlarını görebilsin.
    - Quiz sonucu veritabanına kaydedildi mi kolayca kontrol edilsin.
    """

    quiz_results = get_quiz_results_by_plan(plan_id)

    if not quiz_results:
        st.info("Bu plan için henüz kaydedilmiş quiz sonucu yok.")
        return

    st.markdown("### 🧪 Kaydedilmiş Quiz Sonuçları")

    for result in quiz_results:
        with st.container(border=True):
            col_title, col_score, col_date = st.columns([2, 1, 1])

            with col_title:
                st.write(f'**{result["quiz_title"]}**')
                st.caption(f'Plan ID: {result["plan_id"]} | Hafta ID: {result["week_id"]}')

            with col_score:
                st.metric(
                    "Skor",
                    f'{result["correct_count"]}/{result["total_questions"]}'
                )

            with col_date:
                created_at = result.get("created_at", "")
                st.caption("Oluşturulma")
                st.write(created_at[:19].replace("T", " "))

            score_percentage = result.get("score_percentage", 0)

            # Backend yüzdeyi 0-100 arasında döndürdüğü için Streamlit progress 0-1 arası bekler.
            st.progress(score_percentage / 100)

            st.write(f'Başarı oranı: **%{score_percentage}**')
            details_json = result.get("details_json")

            if details_json:
                try:
                    details = json.loads(details_json)
                except json.JSONDecodeError:
                    details = []

                if details:
                    with st.expander("Soru ve Cevap Detaylarını Göster", expanded=False):
                        for item in details:
                            with st.container(border=True):
                                if item.get("is_correct"):
                                    st.success(f'Soru {item.get("question_number")}: Doğru')
                                else:
                                    st.error(f'Soru {item.get("question_number")}: Yanlış')

                                st.write(f'**Soru:** {item.get("question")}')
                                st.write(f'**Senin cevabın:** {item.get("selected_answer")}')
                                st.write(f'**Doğru cevap:** {item.get("correct_answer")}')
                                st.info(f'**Açıklama:** {item.get("explanation")}')

# ============================================================
# MAIN UI
# ============================================================

st.title("🎓 AI Destekli Kişisel Öğrenme Planlayıcı")

st.write(
    "Öğrenmek istediğin konuyu gir, sistem sana kişisel bir öğrenme planı oluştursun."
)

render_dashboard_overview()
st.divider()

if st.session_state.success_message:
    st.success(st.session_state.success_message)
    st.session_state.success_message = None

# ============================================================
# PLAN GENERATION FORM
# ============================================================
# Yeni plan oluşturma alanını expander içine aldık.
# Böylece dashboard ve aktif plan ekranı daha temiz görünür.
with st.expander("➕ Yeni Öğrenme Planı Oluştur", expanded=True):
    with st.form("generate_plan_form"):
        topic = st.text_input(
            "Öğrenmek istediğin konu",
            placeholder="Örn: Python, React, Yapay Zeka, Veri Analizi"
        )

        level = st.selectbox(
            "Mevcut seviyen",
            ["Başlangıç", "Orta", "İleri"]
        )

        goal = st.text_area(
            "Hedefin",
            placeholder="Örn: Staj için temel Python öğrenmek istiyorum."
        )

        col_time, col_duration = st.columns(2)

        with col_time:
            weekly_hours = st.number_input(
                "Haftalık kaç saat ayırabilirsin?",
                min_value=1,
                max_value=40,
                value=5
            )

        with col_duration:
            duration_weeks = st.number_input(
                "Kaç haftalık plan istiyorsun?",
                min_value=1,
                max_value=24,
                value=4
            )

        learning_preference = st.selectbox(
            "Öğrenme tercihin",
            [
                "Karışık",
                "Video ağırlıklı",
                "Yazılı kaynak ağırlıklı",
                "Uygulamalı proje ağırlıklı",
                "Quiz ve tekrar ağırlıklı"
            ]
        )

        submitted = st.form_submit_button("Plan Oluştur")


# ============================================================
# FORM SUBMIT HANDLING
# ============================================================

if submitted:
    if not topic.strip() or not goal.strip():
        st.warning("Lütfen konu ve hedef alanlarını doldur.")

    else:
        # Formdan gelen değerleri FastAPI'ye gönderilecek payload formatına çeviriyoruz.
        payload = {
            "topic": topic,
            "level": level,
            "goal": goal,
            "weekly_hours": int(weekly_hours),
            "duration_weeks": int(duration_weeks),
            "learning_preference": learning_preference
        }

        with st.spinner("Plan oluşturuluyor..."):
            plan, error = generate_plan(payload)

        if plan:
            # Yeni oluşturulan planı aktif plan olarak kaydediyoruz.
            # Böylece sayfa yenilense bile plan detayı açık kalır.
            st.session_state.active_plan_id = plan["id"]
            st.session_state.last_created_plan_id = plan["id"]

            # st.rerun() sonrası da başarı mesajının görünmesi için session_state'e yazıyoruz.
            st.session_state.success_message = "Plan başarıyla oluşturuldu!"

            st.rerun()

        else:
            st.error("Plan oluşturulamadı.")
            st.code(error)


st.divider()


# ============================================================
# ACTIVE PLAN DETAIL
# ============================================================
# Eğer aktif plan varsa backend'den güncel halini çekip detayını gösteriyoruz.
# Checkbox güncellemelerinden sonra da bu bölüm tekrar render edilir.
if st.session_state.active_plan_id is not None:
    active_plan = get_plan_by_id(st.session_state.active_plan_id)

    if active_plan:
        st.subheader("📖 Aktif Öğrenme Planı")
        render_plan_detail(active_plan)

    else:
        st.warning("Aktif plan bulunamadı veya backend'den alınamadı.")


st.divider()


# ============================================================
# SAVED PLANS LIST
# ============================================================
# Veritabanında kayıtlı tüm planları listeler.
render_saved_plans()