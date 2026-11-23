# Pion Audio Tools Local

Tạo và duyệt audio tiếng Trung bằng Kokoro / MeloTTS trên máy cá nhân. Chưa nối CMS hoặc R2, không dùng API TTS trả phí.

## Windows: cài Kokoro lần đầu

Cần **Python 3.11 hoặc 3.12 x64** và [Git](https://git-scm.com/downloads/win). Xem Python đã cài bằng `py -0p`; tải thêm tại [python.org](https://www.python.org/downloads/windows/) nếu thiếu.

Mở terminal ở thư mục dự án, chạy lần lượt:

```powershell
git clone https://github.com/toainguyen1504/audio-tools-local.git
cd audio-tools-local
powershell -ExecutionPolicy Bypass -File .\scripts\setup-kokoro.ps1
```

Đã clone thì chỉ cần vào thư mục đó, chạy `git pull origin main` rồi lệnh setup. Script tự chọn Python x64 3.12 hoặc 3.11, tạo `.venv-kokoro`, cài thư viện và tải model (khoảng 350–400 MB, chưa tính thư viện).

## Mở và thử

Mở **`start.cmd`**, hoặc chạy:

```powershell
.\.venv-kokoro\Scripts\python.exe -m pion_audio.server
```

Vào **http://127.0.0.1:8765** → chọn model, giọng, tốc độ → **Tạo mẫu nghe thử** hoặc **Tạo 20 mẫu**. Giữ terminal đang chạy. Lần sau chỉ cần mở lại, không cài lại.

- Giọng mặc định: **Kokoro `zf_001`**, **MeloTTS `ZH`**; danh sách lấy từ model đã tải.
- Tốc độ: **0.5 / 0.75 / 0.85 / 1.0 / 1.25 / 1.5**, mặc định **1.0**. Mức 0.5/1.5 có thể kém tự nhiên.
- Chọn **Đạt / Cần thay / Để sau** sau khi batch kết thúc. Pinyin chỉ để đối chiếu, chưa ép cách đọc; cần nghe duyệt thanh điệu và từ đa âm.
- **Tiếp tục đợt trước / Thử lại mục lỗi** giữ cấu hình cũ và dùng lại file đã có.
- **Xuất ZIP audio + ID** mặc định chỉ lấy mẫu đã duyệt; bỏ chọn để xuất toàn bộ mẫu tạo thành công.

## Thêm MeloTTS (tùy chọn)

Cần thêm **Python 3.10 x64**, sau đó chạy:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-melo.ps1
```

Trong giao diện chọn **MeloTTS → Chuẩn bị model**, chờ trạng thái **Sẵn sàng**, rồi tạo audio. Dùng chung giao diện, không mở server khác. Cài lần đầu có thể tải vài GB dữ liệu. Upstream khuyến nghị Docker trên Windows; script native vẫn cần kiểm tra trên máy bạn.

## Danh sách lớn

Chọn file JSON, tối đa 10.000 mục, ID duy nhất và nội dung tối đa 300 ký tự/mục:

```json
[
  {"id":"vocab:123","text":"银行","pinyin":"yínháng","meaning":"ngân hàng"},
  {"id":"example:456","text":"我喜欢学习中文。"}
]
```

`id`, `text` bắt buộc; `pinyin`, `meaning`, `kind`, `note` tùy chọn. Kết quả nằm trong `output/<model>`; WAV cũ được giữ, bảng kết quả đợt trước lưu ở `history`. Model và cache nằm trong `models`, không đưa lên Git.

## Khi có lỗi

- **Không tìm thấy Python:** chạy `py -0p`; Kokoro cần 3.11/3.12 x64, Melo cần 3.10 x64. `python --version` xem phiên bản; `python -v` bật log, nhập `exit()` nếu thấy `>>>`.
- **Thiếu thư viện:** chạy lại script setup đúng model, bấm **Kiểm tra lại**. Không cài chung hai môi trường.
- **Thiếu model:** bấm **Chuẩn bị model**, xem **Nhật ký xử lý**. Nếu lỗi, gửi các dòng cuối log.
- **Không mở được giao diện:** giữ server chạy, không dùng Live Server. Cổng bận thì thêm `--port 8766` vào lệnh mở.

## Linux / macOS

```bash
python3.12 -m venv .venv-kokoro
.venv-kokoro/bin/python -m pip install -r requirements/kokoro.txt
.venv-kokoro/bin/python -m pion_audio.download
.venv-kokoro/bin/python -m pion_audio.server
```

Kiểm tra: `python -m unittest discover -s tests -v`. Chi tiết kết quả tại [VALIDATION.md](VALIDATION.md).

Nguồn: [Kokoro model](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh) (Apache-2.0), [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) (MIT), [MeloTTS](https://github.com/myshell-ai/MeloTTS) (MIT). Giữ thông báo giấy phép upstream khi phân phối lại. Tự chạy không mất phí API TTS, vẫn dùng tài nguyên máy và nơi lưu audio.
