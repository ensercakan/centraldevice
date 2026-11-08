# centraldevice

Merkezi ağ cihazı yönetim platformu: access point, repeater, modem, switch ve router cihazlarını tek bir web arayüzünden izleme ve yapılandırma.

## Özellikler

- **Envanter ve izleme:** Cihaz listesi, durum (up/down), SNMP ile metrik toplama (sysDescr, uptime, arayüzler, CPU/bellek), otomatik ağ taraması (discovery)
- **Uzaktan yapılandırma:** SSH/CLI (Netmiko), TR-069/CWMP (modemler), vendor REST API (UniFi/Meraki vb.), SNMP üzerinden okuma
- **İş kuyruğu:** Poll, config push, firmware, reboot, discovery işleri Celery ile arka planda; durum takibi ve yeniden deneme
- **Alarmlar:** Cihaz düşmesi ve iş hatalarında otomatik alarm, onaylama akışı
- **Güvenlik:** JWT kimlik doğrulama, rol bazlı yetkilendirme (admin / operator / viewer), cihaz kimlik bilgilerinin Fernet ile şifreli saklanması, tüm kritik işlemlerin audit logu
- **Web arayüzü:** React tabanlı dashboard, cihaz detayları, iş ve alarm sayfaları

## Mimari

```
┌────────────┐     ┌─────────────┐     ┌────────────────────────────┐
│  Frontend  │────▶│   Backend   │────▶│  PostgreSQL (veri)         │
│ React+Vite │◀────│ FastAPI     │────▶│  Redis (kuyruk)            │
└────────────┘     │  Celery     │────▶│  SNMP / SSH / TR-069 / REST│
                   │  worker+beat│     │  (cihazlar)                │
                   └─────────────┘     └────────────────────────────┘
```

Ayrıntılı mimari için [docs/architecture.md](docs/architecture.md).

## Hızlı Başlangıç (Docker)

```bash
cp backend/.env.example backend/.env
# backend/.env içinde SECRET_KEY ve BOOTSTRAP_ADMIN_PASSWORD değerlerini değiştirin
docker compose up --build
```

- Web arayüzü: http://localhost:8080 (ilk kullanıcı: `.env` içindeki admin bilgileri)
- API: http://localhost:8000 (OpenAPI dokümanı: http://localhost:8000/docs)

## Yerel Geliştirme

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Worker (ayrı terminalde, Redis çalışırken):

```bash
celery -A app.tasks.celery_app:celery_app worker --loglevel=info
celery -A app.tasks.celery_app:celery_app beat --loglevel=info
```

Frontend:

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, /api istekleri :8000'e proxy'lenir
```

Varsayılan olarak SQLite kullanılır (`DATABASE_URL` verilmezse); üretimde PostgreSQL önerilir.

## API Özeti

| Yöntem | Yol | Açıklama |
| --- | --- | --- |
| POST | `/api/auth/login` | JWT token alır (form: username/password) |
| GET | `/api/auth/me` | Giriş yapan kullanıcı |
| GET/POST | `/api/devices` | Cihaz listeleme / ekleme |
| POST | `/api/devices/discover` | Ağ taraması başlatır (`{"subnet": "192.168.1.0/24"}`) |
| GET/PATCH/DELETE | `/api/devices/{id}` | Cihaz detay / güncelle / sil |
| POST | `/api/devices/{id}/credentials` | Şifreli kimlik bilgisi ekle |
| POST | `/api/devices/{id}/poll` | SNMP poll iş kuyruğa alır |
| POST | `/api/devices/{id}/config` | Config push (`template` + `variables`) |
| POST | `/api/devices/{id}/reboot` | Cihazı yeniden başlatır |
| GET | `/api/devices/{id}/metrics` | Toplanan metrikler |
| GET | `/api/jobs`, POST `/api/jobs/{id}/retry` | İşler |
| GET | `/api/alerts`, POST `/api/alerts/{id}/acknowledge` | Alarmlar |
| GET | `/api/dashboard/summary` | Özet istatistikler |
| GET/POST/PATCH | `/api/users` | Kullanıcı yönetimi (sadece admin) |

## Roller

- **admin:** tüm işlemler + kullanıcı yönetimi + cihaz silme
- **operator:** cihaz ekleme/güncelleme, kimlik bilgisi ekleme, poll/config/reboot, alarm onaylama
- **viewer:** salt okuma

## Güvenlik Notları

- `SECRET_KEY` ve `VAULT_KEY` mutlaka üretimde değiştirilmeli (bkz. `backend/.env.example`)
- Cihaz şifreleri/community stringleri veritabanında Fernet ile şifreli tutulur; API asla düz metin döndürmez
- Üretimde HTTPS arkasına alınmalı, CORS sadece gerekli origin'lere açılmalı
