# centraldevice — Mimari Dokümanı

## 1. Amaç

Access point, repeater, modem, switch, router gibi ağ cihazlarının tek bir merkezden izlenmesi (monitoring) ve yapılandırılması (configuration management).

## 2. Bileşenler

| Bileşen | Teknoloji | Görev |
| --- | --- | --- |
| frontend | React 18 + Vite, nginx (prod) | Web arayüzü: dashboard, cihazlar, detay, işler, alarmlar, kullanıcılar |
| backend | Python 3.12 + FastAPI | REST API, kimlik doğrulama (JWT), RBAC, audit log |
| worker | Celery worker | SNMP poll, config push, firmware, reboot, discovery işlerini çalıştırır |
| beat | Celery beat | Periyodik SNMP poll (`POLL_INTERVAL_SECONDS`) |
| db | PostgreSQL (geliştirmede SQLite) | Kullanıcılar, cihazlar, kimlik bilgileri, işler, alarmlar, metrikler, audit |
| redis | Redis | Celery broker + result backend |

## 3. Veri Modeli

- `users` — JWT kimlik doğrulama, rol (admin/operator/viewer)
- `devices` — hostname, IP, tip (router/switch/access_point/repeater/modem), vendor/model/serial, durum, site, `management_url` (REST/TR-069 için)
- `credentials` — cihaza özel veya global kimlik bilgileri; secret Fernet ile şifreli (`encrypted_secret`), API düz metin döndürmez
- `jobs` — kuyruktaki/çalışan/biten işler; payload/result JSON, durum (queued/running/succeeded/failed)
- `alerts` — cihaz düşmesi ve iş hataları; onaylanabilir
- `device_metrics` — SNMP ile toplanan zaman serisi (sysUpTime, arayüz sayısı, CPU %, bellek %, ...)
- `audit_logs` — kim, ne zaman, ne yaptı

## 4. Cihaz Erişim Katmanı

| Yöntem | Kullanım | Implementasyon |
| --- | --- | --- |
| SNMP v2c | İzleme (poll), discovery | `pysnmp` — sysDescr/sysObjectID/ifTable/hrStorage/hrProcessor/entPhysical |
| SSH/CLI | Yapılandırma değişikliği, reboot | `netmiko` (`send_config_set` + `save_config`) |
| TR-069/CWMP | Modem/CPE yönetimi, firmware | SOAP zarfları ile `GetParameterValues`, `SetParameterValues`, `Reboot`, `Download` RPC'leri (`httpx`) |
| Vendor REST | UniFi/Meraki/Omada vb. | Generic `VendorRestClient`: login (Bearer) + cihaz listesi + WLAN config + reboot |

Cihaz tipi algılama: SNMP `sysObjectID` üretici prefix'i + `sysDescr` anahtar kelimeleriyle (router/switch/ap/repeater/modem).

## 5. İş Akışları

1. **Poll:** beat her `POLL_INTERVAL_SECONDS`'ta tüm cihazları kuyruğa alır → SNMP poll → metrikler yazılır, durum güncellenir, cihaz düşerse alarm açılır.
2. **Discovery:** kullanıcı subnet verir → ping taraması → canlı hostlarda SNMP probe → yeni cihazlar otomatik eklenir.
3. **Config push:** kullanıcı şablon + değişkenler gönderir → cihaza uygun kimlik bilgisi seçilir → yönteme göre SSH/TR-069/REST ile uygulanır → sonuç `jobs` tablosuna yazılır.
4. **Firmware:** TR-069 `Download` RPC'si ile ACS üzerinden bellenim indirme.
5. **Reboot:** TR-069 `Reboot` / vendor REST / SSH `reload`.

Broker (Redis) erişilemez durumdaysa API işi senkron çalıştırır; bu geliştirme/test kolaylığı içindir.

## 6. Güvenlik

- PBKDF2-HMAC-SHA256 (200k iterasyon) ile şifre hash'leme
- HS256 JWT, süre kontrollü (`ACCESS_TOKEN_EXPIRE_MINUTES`)
- RBAC: admin > operator > viewer (endpoint bazlı `require_roles`)
- Kimlik bilgileri Fernet (AES-128-CBC + HMAC) ile şifreli; anahtar `VAULT_KEY` env veya `.vault_key` dosyasında (git'e girmez)
- Tüm yazma işlemleri `audit_logs`'a kaydedilir
- Üretimde: HTTPS, kısıtlı CORS, güçlü secret değerleri

## 7. Ölçeklendirme Notları

- Metrik hacmi büyürse `device_metrics` yerine TimescaleDB/InfluxDB'ye geçilebilir
- Çok sayıda cihazda worker `concurrency` artırılır, SNMP timeout/retries ayarlanır
- Cihaz grupları/site bazlı toplu işlemler için job fan-out pattern'i uygulanabilir
- Üretim migration'ları için Alembic eklenebilir (prototipte `create_all`)
