# HCMUTE ARS – Production deployment

## 1. Cấu hình `.env`

Sao chép `.env.example` thành `.env` và điền secret/credentials thật.

Tạo secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Đặt:

```env
APP_ENV=production
FLASK_SECRET_KEY=<secret-vừa-tạo>
RESET_OTP_CONSOLE=0
MQTT_TLS_INSECURE=0
```

Không commit `.env` vào Git.

## 2. Virtualenv và dependency

```bash
cd /opt/hcmute-ars
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Build tài nguyên giao diện trước khi triển khai (Node.js 20 trở lên chỉ cần ở bước build):

```bash
npm ci
npm run build
```

Các tệp được phục vụ từ `static/`; máy chủ production không cần tải Tailwind,
Font Awesome, Chart.js hoặc font từ CDN khi người dùng truy cập.

## 3. Kiểm thử và CI

Chạy bộ kiểm thử trước khi phát hành:

```bash
pip install -r requirements-dev.txt
pytest -q
npm ci
npm run build
```

GitHub Actions chạy các bước này khi push hoặc mở pull request. Không đặt
credentials production trong pipeline kiểm thử.

## 4. Quyền file

User chạy service phải có quyền đọc/ghi `database.db` và thư mục ứng dụng. Không chạy Flask/Gunicorn bằng `root`.

Ví dụ:

```bash
sudo chown -R ars:ars /opt/hcmute-ars
chmod 600 /opt/hcmute-ars/.env
chmod 660 /opt/hcmute-ars/database.db
```

## 5. Chạy bằng Gunicorn

Không dùng `flask run` hoặc `app.run(debug=True)` trên Internet.

Ứng dụng hiện dùng SQLite và MQTT/Serial trong cùng process, vì vậy bản triển khai hiện tại nên dùng **1 Gunicorn worker**; tăng worker có thể tạo nhiều MQTT subscriber/Serial reader.

```bash
.venv/bin/gunicorn --workers 1 --threads 4 --timeout 120 --bind 127.0.0.1:5000 wsgi:app
```

## 6. systemd

Dùng file `hcmute-ars.service.example`, đổi `/opt/hcmute-ars` và user `ars` nếu cần, sau đó:

```bash
sudo cp hcmute-ars.service.example /etc/systemd/system/hcmute-ars.service
sudo systemctl daemon-reload
sudo systemctl enable --now hcmute-ars
sudo systemctl status hcmute-ars
journalctl -u hcmute-ars -f
```

## 7. Nginx + HTTPS

Dùng `nginx.conf.example` làm reverse proxy tới `127.0.0.1:5000`.

Sau khi DNS trỏ domain về server, cấp TLS bằng Certbot/Let's Encrypt rồi chuyển listener public sang HTTPS.

HTTPS là bắt buộc trong production vì ứng dụng có session cookie, tài khoản giảng viên và bearer token của lượt làm bài.

## 8. Health check và theo dõi

- Uptime monitor bên ngoài nên kiểm tra `https://your-domain/health/ready`
  mỗi phút; `/health/live` chỉ xác nhận process đang trả lời.
- `journalctl -u hcmute-ars` chứa log vận hành; cấu hình cảnh báo khi service
  dừng, disk gần đầy hoặc health check lỗi.
- Giảng viên đăng nhập có thể xem trạng thái MQTT trong giao diện. Trạng thái
  không trả payload phản hồi hoặc MSSV; log server cũng không ghi payload MQTT.
- Theo dõi tuổi của bản backup gần nhất và thực hiện khôi phục thử theo lịch.

## 9. Backup và khôi phục SQLite

Tạo backup nhất quán khi ứng dụng vẫn đang chạy:

```bash
cd /opt/hcmute-ars
.venv/bin/python scripts/database_maintenance.py backup --directory /var/backups/hcmute-ars
```

Kiểm tra backup:

```bash
.venv/bin/python scripts/database_maintenance.py verify /var/backups/hcmute-ars/<backup-file>
```

Khôi phục cần đưa ứng dụng về bảo trì/dừng service trước, sao chép backup ra
một vị trí làm việc an toàn, rồi chạy:

```bash
sudo systemctl stop hcmute-ars
.venv/bin/python scripts/database_maintenance.py restore /var/backups/hcmute-ars/<backup-file>
.venv/bin/python scripts/database_maintenance.py verify /opt/hcmute-ars/database.db
sudo systemctl start hcmute-ars
```

Lệnh restore kiểm tra integrity, ghi file tạm cạnh database đích rồi thay thế
nguyên tử. Script không tự xóa backup; đơn vị vận hành cần cấu hình lưu giữ,
mã hóa, phân quyền và xóa bản sao lưu theo chính sách dữ liệu. Database và
backup đều chứa thông tin sinh viên, nên không đặt backup trong web root hoặc
commit vào Git.

Có thể bật backup hằng ngày bằng systemd timer mẫu. Tạo thư mục backup riêng
ngoài web root và cấp quyền cho user service:

```bash
sudo install -d -o ars -g ars -m 700 /var/backups/hcmute-ars
sudo cp hcmute-ars-backup.service.example /etc/systemd/system/hcmute-ars-backup.service
sudo cp hcmute-ars-backup.timer.example /etc/systemd/system/hcmute-ars-backup.timer
sudo systemctl daemon-reload
sudo systemctl enable --now hcmute-ars-backup.timer
systemctl list-timers hcmute-ars-backup.timer
```

Timer không xóa backup cũ. Theo dõi dung lượng ổ đĩa và áp dụng lịch lưu giữ
đã được đơn vị phê duyệt; kiểm tra định kỳ rằng file mới nhất vượt qua lệnh
`verify` và khôi phục thử được.

## 10. Những gì đã được harden trong code

- `FLASK_SECRET_KEY` production bắt buộc, không còn secret mặc định cố định.
- Session cookie: `HttpOnly`, `SameSite=Lax`, `Secure` trong production.
- Flask debug/reloader bị tắt khi chạy production.
- `ProxyFix` cho deployment sau reverse proxy.
- CSRF/origin check cho các API thay đổi trạng thái.
- Rate limit cho login, register, password reset và các endpoint tra cứu/bắt đầu bài thi.
- Giới hạn kích thước request/upload.
- `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `COOP` và HSTS khi HTTPS.
- SQLite bật foreign keys và busy timeout.
- Không cho production dùng MQTT TLS insecure.
- Không cho production in OTP ra console.
- API response được đánh `no-store` để giảm nguy cơ cache dữ liệu nhạy cảm.
- Health check readiness/liveness; MQTT status được trả ở dạng đã lược bỏ payload.
- Có trang và tài liệu quyền riêng tư dạng mẫu; đơn vị triển khai phải điền
  đầu mối liên hệ, nhà cung cấp và địa điểm lưu trữ thực tế trước khi mở dịch vụ.

## 11. Lộ trình mở rộng

```text
Internet
   |
 HTTPS :443
   |
 Nginx / Cloudflare
   |
 127.0.0.1:5000
   |
 Gunicorn (1 worker, 4 threads)
   |
 Flask app
   |------ SQLite database.db
   |------ MQTT broker (TLS 8883)
   `------ Serial ESP32 gateway (nếu ENABLE_HARDWARE=1)
```

Giữ một worker khi còn SQLite và MQTT/Serial trong process này. Trước khi
tăng số worker hoặc chạy nhiều máy chủ:

1. Đo tải với số lớp thi đồng thời dự kiến và đặt ngưỡng chấp nhận cho độ trễ,
   lỗi ghi đáp án và thời gian phản hồi.
2. Chuyển dữ liệu sang PostgreSQL, kiểm thử migration/rollback và chạy kiểm tra
   tương đương trên một bản sao staging.
3. Chuyển rate-limit/session dùng chung sang Redis hoặc dịch vụ tương đương.
4. Tách MQTT/Serial consumer thành worker đơn thể để web replicas không nhân
   bản subscriber/reader.
5. Chỉ tăng replicas sau khi kiểm thử tải, khôi phục backup và xử lý sự cố đạt
   tiêu chí đã thống nhất.

## 12. Quyền riêng tư và trước khi mở công khai

Xem [PRIVACY_POLICY.md](./PRIVACY_POLICY.md) và trang `/privacy`. Phiên bản
hiện tại không tự xóa dữ liệu; giảng viên/quản trị viên chủ động xóa. Đây là
thông báo mẫu, không phải xác nhận tuân thủ pháp luật. Cần rà soát pháp lý,
đầu mối quyền riêng tư và thông tin nhà cung cấp thực tế trước khi nhận dữ liệu
thật.

Trước khi bật tự đăng ký công khai, cần bổ sung xác minh quyền sở hữu email/số
điện thoại và quy trình onboarding do đơn vị phê duyệt.
