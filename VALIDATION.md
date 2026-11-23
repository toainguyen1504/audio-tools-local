# Kiểm tra bản local

Ngày 23/11/2026, Linux x86_64. Chưa thực thi PowerShell/CMD trực tiếp trên Windows.

## Đã đạt

- **34 test Python:** dữ liệu đầu vào, giới hạn tốc độ, giọng lấy từ model, cache, dừng/tiếp tục, thử lại, duyệt, lỗi khởi tạo và ZIP theo ID.
- **UI smoke (jsdom):** 5 giọng Kokoro / ZH, mặc định an toàn, nhớ lựa chọn, 6 tốc độ, nghe thử, duyệt, khóa thao tác khi đang chạy, phân trang 123 mục và từ chối JSON lỗi. Không phải kiểm tra hình ảnh bằng trình duyệt thật.
- `node --check web/app.js` và `git diff --check`: đạt.
- Model thật: Kokoro `v1.1-zh` và MeloTTS-Chinese đã tạo 20/20 mẫu trong vòng kiểm tra đầu. Vòng này đã kiểm tra cả 6 tốc độ trên hai model và tạo thêm mẫu bằng cả 5 giọng Kokoro được đưa vào dropdown.
- Độ dài cùng câu ở tốc độ 0.5 / 1.5: Kokoro **4,536 / 1,536 giây**, MeloTTS **3,281 / 1,276 giây**. Đây là độ dài audio, không phải thời gian xử lý.
- **HTTP + worker thật:** chuẩn bị Melo, nghe thử hai model, tạo batch, duyệt, xuất ZIP chỉ mẫu đạt / toàn bộ, thử lại 1 file lỗi trong 3 file và dùng lại 2 file còn tốt; giữ duyệt cho file dùng lại, lưu bảng kết quả cũ trong history.

## Chạy lại

```bash
python -m unittest discover -s tests -v
.venv-kokoro/bin/python -m tests.model_smoke --engine kokoro
.venv-melo/bin/python -m tests.model_smoke --engine melo
python -m tests.http_model_smoke
```

Hai lệnh smoke model cần thư viện/model đã cài; HTTP smoke cần cả hai môi trường và Melo đã chuẩn bị. Chúng tạo dữ liệu thử trong output. UI smoke cần Node + jsdom: `node tests/ui-smoke.cjs /duong-dan/toi/jsdom`.

## Giới hạn

- Thành công kỹ thuật không xác nhận phát âm đúng về mặt sư phạm. Mẫu mới vẫn chờ người dùng nghe duyệt.
- Chưa benchmark hàng nghìn mục, chưa nối CMS/R2/Learning app, chưa kiểm tra thao tác và giao diện trên máy Windows của người dùng.
- Trong môi trường kiểm tra, NLTK downloader từ chối proxy. Dữ liệu được lấy từ repo chính thức nltk/nltk_data và dùng local, không tắt cơ chế bảo vệ. Script Windows dùng downloader thông thường và dừng nếu tải lỗi.
- Không tạo CI/CD, không gọi API TTS trả phí. Model, môi trường Python và output không nằm trong Git.
