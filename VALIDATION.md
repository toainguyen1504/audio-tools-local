# Kiểm tra bản local

Ngày: 23/11/2026. Môi trường thực hiện: Linux x86_64. Chưa chạy trực tiếp trên Windows của người dùng.

## Đã kiểm tra

- 19 test Python: validation đầu vào, cache theo nội dung/cách đọc/giọng/tốc độ, WAV bị hỏng, tiếp tục batch, dừng, lỗi từng mục, model không nạp được, khóa tiến trình, duyệt và HTTP loopback.
- `node --check web/app.js`: đạt.
- DOM smoke bằng jsdom: hiển thị 20 dòng và 20 audio controls, duyệt mẫu, phân trang danh sách 123 mục (50/50/23), từ chối mục JSON không hợp lệ. Đây không phải kiểm tra giao diện bằng trình duyệt thật.
- Kokoro model thật `v1.1-zh`, giọng `zf_001`, tốc độ 1.0: tạo thành công **20/20 WAV PCM 16-bit**, mẫu số hữu hạn và có tín hiệu âm thanh. Tổng độ dài 17,686 giây (không phải thời gian xử lý).
- Gọi HTTP `/api/start` thực tế từ local server → subprocess worker → manifest: hoàn tất, dùng lại **20/20** file Kokoro đã có, exit code 0.
- MeloTTS checkpoint thật `myshell-ai/MeloTTS-Chinese`, giọng `ZH`, PyTorch 2.5.1 CPU trên Python 3.10: tạo thành công **20/20 WAV**, exit code 0. Đã cài UniDic đầy đủ trước khi nạp model.
- Trong môi trường kiểm tra, NLTK downloader từ chối proxy theo cơ chế bảo vệ của NLTK. Đã lấy các gói dữ liệu cố định từ repo chính thức `nltk/nltk_data`, giải nén local và dùng `NLTK_DATA`; không tắt cơ chế bảo vệ. Script Windows dùng downloader thông thường, dừng và báo lỗi nếu tải không được.

## Phạm vi

- Thành công kỹ thuật không xác nhận phát âm đúng về mặt sư phạm. Tất cả mẫu mới vẫn `pending` để người dùng nghe duyệt.
- Chưa kiểm tra tốc độ trên máy Windows, chưa benchmark hàng nghìn mục, chưa nối CMS/R2/Learning app.
- Không tạo CI/CD, không gọi dịch vụ TTS trả phí.
- Model và output bị loại khỏi Git; script setup tải model từ upstream trên máy người dùng.
