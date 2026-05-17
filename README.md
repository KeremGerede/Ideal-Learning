# AI Destekli Kişisel Öğrenme Planlayıcı

Bu proje, kullanıcının öğrenmek istediği konuya, mevcut seviyesine, hedeflerine, haftalık çalışma süresine ve öğrenme tercihine göre yapay zekâ destekli kişisel öğrenme planı oluşturan bir web uygulamasıdır.

Sistem; haftalık görevler, mini projeler, kaynak önerileri, quizler, ilerleme takibi, önceki öğrenme geçmişine göre yeni konu önerileri ve seçili haftayı AI ile yeniden düzenleme özelliklerini içerir.

Proje şu an çalışan bir MVP seviyesindedir ve sunum/demo için hazır durumdadır.

---

## Projenin Amacı

Günümüzde öğrenmek isteyen kullanıcılar çok fazla kaynakla karşılaşmakta, ancak nereden başlayacaklarını, hangi sırayla ilerleyeceklerini ve öğrenme sürecini nasıl takip edeceklerini belirlemekte zorlanmaktadır.

Bu projenin amacı, kullanıcının öğrenme hedefini haftalara bölerek daha yönetilebilir, kişiselleştirilmiş ve takip edilebilir bir öğrenme süreci sunmaktır.

Sistem şu sorulara cevap üretmeyi hedefler:

- Kullanıcı hangi konudan başlamalı?
- Hangi sırayla ilerlemeli?
- Haftalık ne kadar çalışmalı?
- Hangi görevleri tamamlamalı?
- Hangi kaynaklardan yararlanmalı?
- Öğrendiğini nasıl test etmeli?
- İlerleme nasıl takip edilmeli?
- Önceki öğrenme geçmişine göre sırada ne öğrenilebilir?

---

## Temel Özellikler

### Öğrenme Planı

- Gemini API ile kişiselleştirilmiş öğrenme planı oluşturma
- Kullanıcı seviyesi, hedefi, haftalık çalışma süresi ve öğrenme tercihini dikkate alma
- Haftalık görevler, kaynaklar ve mini projeler oluşturma
- Plan özeti ve plan sonu kazanımı üretme
- Planları SQLite veritabanına kaydetme
- Plan listeleme, detay görüntüleme ve silme

### Görev ve İlerleme Takibi

- Haftalık görevleri görüntüleme
- Görevleri tamamlandı/tamamlanmadı olarak işaretleme
- Checkbox kullanıldığında sayfanın en üste atmasını engelleyen local state güncellemesi
- Genel ilerleme yüzdesi hesaplama
- Dashboard üzerinde toplam plan, toplam görev, tamamlanan görev ve genel ilerleme gösterimi

### Quiz Sistemi

- Seçili hafta için Gemini ile quiz oluşturma
- Quiz sorularını çözme
- Skor hesaplama
- Quiz sonucunu veritabanına kaydetme
- Soru/cevap detaylarını `details_json` alanında saklama
- Quiz sonuçlarını listeleme
- Yanlış/doğru cevap detaylarını görüntüleme

### Kaynak Sistemi

- Haftalık kaynak önerileri oluşturma
- Kaynak açıklamalarını haftalık görevlerle ilişkilendirme
- Kaynak türlerine göre rozet gösterimi:
  - Dokümantasyon
  - Makale
  - Kurs
  - YouTube Video
  - Diğer kaynaklar
- Resources sayfasında kaynakları plan/hedef bazlı gruplama
- Kaynak arama ve kaynak tipi filtresi

### AI ile Seçili Haftayı Yeniden Düzenleme

- Plan Detayı sayfasında her hafta için **AI ile Yenile** butonu
- Kullanıcının özel talimat yazabilmesi
- Sadece seçilen haftanın yeniden oluşturulması
- Diğer haftaların korunması
- Seçilen haftanın başlık, açıklama, mini proje, görev ve kaynaklarının yenilenmesi
- Yenilenen haftaya ait eski quiz sonuçlarının temizlenmesi
- Kaynak açıklamalarının yine görevlerle ilişkili tutulması

### Önceki Planlara Göre Öğrenme Önerileri

- Veritabanındaki önceki planları analiz etme
- Gemini ile yeni öğrenme konusu önerileri üretme
- Dashboard üzerinde **Bunları da öğrenmek isteyebilirsiniz** alanı
- Her öneride:
  - Önerilen konu
  - Neden önerildiği
  - Önerilen seviye
  - Önerilen öğrenme tercihi
  - Önerilen hedef
- Gemini çalışmazsa fallback öneri sistemi

### YouTube Video Entegrasyonu

- YouTube Data API ile gerçek video kaynakları arama
- Gemini tarafından üretilen sahte/geçersiz YouTube linklerine güvenmeme
- Embed edilebilir videoları doğrulama
- Video ağırlıklı öğrenme tercihinde daha fazla video önerme
- API kotası dolduğunda sistemin video olmadan çalışmaya devam etmesi

> Not: YouTube Data API kota limiti nedeniyle demo sırasında video kaynakları her zaman gelmeyebilir. Sistem, video kaynakları olmadan da dokümantasyon ve makale kaynaklarıyla çalışacak şekilde tasarlanmıştır.

---

## Kullanılan Teknolojiler

| Katman | Teknoloji | Açıklama |
|---|---|---|
| Backend | FastAPI | REST API geliştirme |
| Veritabanı | SQLite | MVP için hafif ve kolay kurulabilir veritabanı |
| ORM | SQLAlchemy | Veritabanı modelleri ve ilişkiler |
| AI Servisi | Gemini API | Plan, quiz, hafta yenileme ve öneri üretimi |
| Video Servisi | YouTube Data API | Gerçek YouTube video kaynakları |
| Test Arayüzü | Streamlit | Backend geliştirme ve hızlı test |
| Frontend | React | Kullanıcı arayüzü |
| Build Tool | Vite | React geliştirme ortamı |
| Styling | Tailwind CSS | Modern ve responsive tasarım |
| Veri Doğrulama | Pydantic | Request/response şemaları |
| Environment | python-dotenv | API key ve ortam değişkenleri |
| Server | Uvicorn | FastAPI uygulamasını çalıştırma |

---

## Proje Mimarisi

```text
personal-learning-platform/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── ai_service.py
│   │   ├── youtube_service.py
│   │   └── routes/
│   │       ├── plans.py
│   │       ├── tasks.py
│   │       ├── quiz.py
│   │       ├── quiz_results.py
│   │       ├── stats.py
│   │       └── recommendations.py
│   │
│   ├── streamlit_app.py
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── apiClient.js
│   │   ├── components/
│   │   │   ├── Sidebar.jsx
│   │   │   ├── MobileNavigation.jsx
│   │   │   ├── StatCard.jsx
│   │   │   ├── PlanCard.jsx
│   │   │   ├── WeeklyQuizPanel.jsx
│   │   │   └── YouTubeEmbed.jsx
│   │   ├── pages/
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── PlanCreatorPage.jsx
│   │   │   ├── MyPlansPage.jsx
│   │   │   ├── PlanDetailPage.jsx
│   │   │   ├── QuizResultsPage.jsx
│   │   │   └── ResourcesPage.jsx
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   │
│   ├── package.json
│   └── vite.config.js
│
├── README.md
└── .gitignore
```

---

## Kurulum

### 1. Projeyi Klonla

```bash
git clone <repository-url>
cd personal-learning-platform
```

---

## Backend Kurulumu

### 1. Backend klasörüne gir

```bash
cd backend
```

### 2. Sanal ortam oluştur

```bash
python -m venv venv
```

### 3. Sanal ortamı aktif et

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

### 4. Gerekli paketleri kur

```bash
pip install -r requirements.txt
```

### 5. `.env` dosyası oluştur

`backend/.env` dosyası oluştur:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
YOUTUBE_API_KEY=your_youtube_data_api_key_here
```

`YOUTUBE_API_KEY` opsiyoneldir. Girilmezse veya kota dolarsa sistem video kaynağı eklemeden çalışmaya devam eder.

### 6. Backend’i çalıştır

```bash
uvicorn app.main:app --reload
```

Backend çalıştıktan sonra:

```text
Swagger UI:
http://127.0.0.1:8000/docs

Health endpoint:
http://127.0.0.1:8000/health
```

---

## Streamlit Test UI Çalıştırma

Backend klasöründeyken:

```bash
streamlit run streamlit_app.py
```

Streamlit arayüzü:

```text
http://localhost:8501
```

---

## React Frontend Kurulumu

### 1. Frontend klasörüne gir

Proje ana dizinindeyken:

```bash
cd frontend
```

### 2. Paketleri kur

```bash
npm install
```

### 3. Frontend’i çalıştır

```bash
npm run dev
```

React arayüzü:

```text
http://localhost:5173
```

Not: React frontend’in düzgün çalışması için FastAPI backend’in açık olması gerekir.

---

## API Endpointleri

### Genel

```http
GET /
```

API’nin çalışıp çalışmadığını kontrol eder.

```http
GET /health
```

Backend sağlık durumunu döndürür.

---

### Plan Endpointleri

```http
POST /plans/generate
```

Kullanıcı girdilerine göre AI destekli öğrenme planı oluşturur.

```http
GET /plans
```

Tüm öğrenme planlarını listeler.

```http
GET /plans/{plan_id}
```

Belirli bir planı haftaları, görevleri ve kaynaklarıyla getirir.

```http
DELETE /plans/{plan_id}
```

Belirli bir planı siler.

```http
GET /plans/{plan_id}/progress
```

Belirli planın ilerleme yüzdesini döndürür.

```http
PATCH /plans/{plan_id}/weeks/{week_id}/regenerate
```

Seçili haftayı Gemini ile yeniden oluşturur.

Örnek request:

```json
{
  "user_instruction": "Bu haftayı daha uygulama ağırlıklı yap. Görevleri daha teknik, kaynakları görevlerle ilişkili olacak şekilde yenile."
}
```

---

### Görev Endpointleri

```http
PATCH /tasks/{task_id}/complete?is_completed=true
```

Bir görevin tamamlanma durumunu günceller.

---

### Quiz Endpointleri

```http
POST /quiz/plans/{plan_id}/weeks/{week_id}/generate
```

Belirli planın belirli haftası için quiz üretir.

---

### Quiz Sonuçları Endpointleri

```http
POST /quiz-results/
```

Quiz sonucunu veritabanına kaydeder.

```http
GET /quiz-results/
```

Tüm quiz sonuçlarını listeler.

```http
GET /quiz-results/plan/{plan_id}
```

Belirli plana ait quiz sonuçlarını listeler.

```http
GET /quiz-results/week/{week_id}
```

Belirli haftaya ait quiz sonuçlarını listeler.

---

### İstatistik Endpointleri

```http
GET /stats/overview
```

Dashboard için genel istatistikleri döndürür.

---

### Öneri Endpointleri

```http
GET /recommendations/?limit=6
```

Önceki öğrenme planlarına göre Gemini ile yeni öğrenme konusu önerileri üretir.

Örnek response:

```json
{
  "based_on_plan_count": 2,
  "recommendations": [
    {
      "topic": "Django",
      "reason": "Python bilginizi web geliştirme tarafına taşıyabilir.",
      "suggested_level": "Orta",
      "suggested_goal": "Django ile MVC yapısı, model-view-template mantığı ve veritabanı bağlantısını öğrenmek.",
      "suggested_learning_preference": "Uygulama ağırlıklı"
    }
  ]
}
```

---

## Frontend Sayfaları

### Dashboard

- Backend sağlık durumu
- Genel plan/görev istatistikleri
- Quiz istatistikleri
- Önceki planlara göre AI destekli öğrenme önerileri

### Plan Oluştur

- Konu
- Seviye
- Öğrenme hedefi
- Haftalık çalışma süresi
- Plan süresi
- Öğrenme tercihi

Plan oluşturulduktan sonra kullanıcı doğrudan plan detayına gidebilir.

### Planlarım

- Kayıtlı planları listeleme
- Plan detayına gitme
- Plan silme

### Plan Detayı

- Plan özeti
- Plan sonu kazanım
- Accordion haftalık görünüm
- Görevler
- Mini proje
- Kaynaklar
- Kaynak türü rozetleri
- Haftalık quiz paneli
- AI ile seçili haftayı yenileme

### Quiz Sonuçları

- Tüm quiz sonuçlarını listeleme
- Quiz detaylarını görüntüleme
- Doğru/yanlış cevap analizi

### Resources

- Tüm planlardaki kaynakları görüntüleme
- Hedef/plan bazlı gruplama
- Arama
- Kaynak tipi filtresi
- YouTube embed player desteği

---

## Örnek Kullanıcı Akışı

1. Kullanıcı Plan Oluştur sayfasına gider.
2. Öğrenmek istediği konu, seviye, hedef, haftalık süre ve tercih bilgisini girer.
3. Backend Gemini API ile kişiselleştirilmiş öğrenme planı üretir.
4. Plan haftalara, görevlere, kaynaklara ve mini projelere ayrılır.
5. Kullanıcı Plan Detayı sayfasında görevleri takip eder.
6. Kullanıcı isterse seçili haftayı AI ile yeniden düzenler.
7. Kullanıcı haftalık quiz oluşturur ve çözer.
8. Quiz sonucu veritabanına kaydedilir.
9. Dashboard’da ilerleme ve quiz metrikleri güncellenir.
10. Sistem önceki planlara göre yeni öğrenme önerileri üretir.

---

## `.gitignore` 

```gitignore
# Node / React
node_modules/
frontend/node_modules/
frontend/dist/

# Environment variables
.env
.env.local
.env.*.local

# Python virtual environments
venv/
.venv/

# Python cache
__pycache__/
*.pyc

# SQLite database
*.db
*.db-shm
*.db-wal

# OS / IDE
.DS_Store
Thumbs.db
.vscode/
.idea/
```

---

## Bilinçli Olarak Eklenmeyen Özellikler

Bu MVP kapsamında bazı özellikler bilinçli olarak ertelenmiştir:

- Kullanıcı kayıt/giriş sistemi
- Kullanıcı bazlı plan ayrımı
- Admin panel
- RAG tabanlı kişisel kaynak havuzu
- Deployment
- Mobil uygulama

Bu özellikler gelecek geliştirme aşamalarında eklenebilir.

---

## Gelecek Geliştirmeler

- Kullanıcı kayıt/giriş sistemi
- Kullanıcıya özel öğrenme geçmişi
- Quiz sonuçlarına göre zayıf konu analizi
- Yanlış cevaplara göre kaynak önerme
- Plan düzenleme ve manuel görev/kaynak ekleme
- RAG destekli kişisel dokümanlardan öğrenme
- YouTube API cache sistemi
- Deployment
- Mobil uygulama

---

## Proje Durumu

Proje şu an çalışan ve sunuma hazır bir MVP seviyesindedir.

Tamamlanan ana parçalar:

- FastAPI backend
- SQLite veritabanı
- Gemini API entegrasyonu
- YouTube Data API entegrasyonu
- React + Vite + Tailwind frontend
- Streamlit test UI
- Plan oluşturma
- Plan listeleme/detay/silme
- Görev takibi
- Quiz üretimi ve sonuç kaydı
- Kaynak yönetimi
- AI ile seçili hafta yenileme
- Önceki planlara göre AI öğrenme önerileri
- Responsive desktop/mobile navigation
