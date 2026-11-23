# Pion Audio Tools Local

Công cụ nội bộ tạo và nghe đối chiếu audio tiếng Trung bằng **Kokoro v1.1-zh** và **MeloTTS**. Chạy trên máy của người nhập liệu, không dùng API TTS trả phí.

## Bắt đầu trên Windows

### 1. Chuẩn bị

- Cài **Python 3.12 x64** từ https://www.python.org/downloads/ (cho Kokoro và giao diện).
- Cài Git: https://git-scm.com/downloads/win.
- Nếu muốn thử MeloTTS, cài thêm **Python 3.10 x64**. Hai model dùng môi trường riêng, không cài chung thư viện.
- Không dùng Python 32-bit hoặc Python 3.14 cho các lệnh dưới đây.

Mở PowerShell, chạy:

```powershell
git clone https://github.com/toainguyen1504/audio-tools-local.git
cd audio-tools-local
py -0p
powershell -ExecutionPolicy Bypass -File .\scripts\setup-kokoro.ps1
```

Lệnh cài tải thư viện và khoảng 350 MB model/giọng/config từ nguồn upstream. Cần internet khi cài; Kokoro có thể tạo audio offline sau khi đã tải đủ dữ liệu. Không cần Azure key, tài khoản Hugging Face hoặc GPU.

### 2. Mở giao diện

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

Hoặc mở `start.cmd`. Trình duyệt mở **http://127.0.0.1:8765**. Chọn **Kokoro**, giọng **zf_001**, tốc độ **1.0**, nhấn **Tạo / tiếp tục 20 mẫu**.

Giữ cửa sổ terminal trong lúc tạo. Giao diện chỉ chạy loopback trên máy bạn, không phải website cần deploy. Nếu cổng bận: `py -3.12 -m pion_audio.server --port 8766`.

### 3. So sánh MeloTTS (tùy chọn)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-melo.ps1
```

Trong giao diện, chọn **MeloTTS**, giọng **ZH**, tạo cùng bộ mẫu. Script cài PyTorch CPU và dữ liệu UniDic theo hướng dẫn upstream; dù chỉ đọc tiếng Trung, Melo vẫn nạp module ngôn ngữ khác. Lần đầu sẽ tải thêm checkpoint và dữ liệu xử lý ngôn ngữ; tổng dung lượng cài có thể vài GB và mất nhiều thời gian hơn Kokoro. Chạy lần lượt hai model để giảm RAM. Mỗi cột ghi đúng giọng và tốc độ trong phần tiến độ.

**MeloTTS trên Windows:** upstream khuyến nghị Docker để giảm vấn đề tương thích. Script native được cung cấp để thử trên Python 3.10; chưa cam kết hoạt động trên mọi máy Windows. Nếu lỗi thư viện, gửi log; không cài Melo vào môi trường Kokoro. Hướng dẫn upstream: https://github.com/myshell-ai/MeloTTS/blob/main/docs/install.md.

## Dùng với hàng nghìn từ

Chọn danh sách JSON thay vì nhập từng mục. Ví dụ:

```json
[
  {"id": "vocab:123", "text": "银行", "pinyin": "yínháng", "meaning": "ngân hàng", "kind": "word"},
  {"id": "example:456", "text": "我喜欢学习中文。", "pinyin": "Wǒ xǐhuan xuéxí Zhōngwén.", "kind": "sentence"}
]
```

- `id` và `text` bắt buộc; `pinyin`, `meaning`, `kind`, `note` tùy chọn.
- ID duy nhất, tối đa 100 ký tự Latin/số/`_ . : -`. Tối đa 10.000 mục, mỗi nội dung 300 ký tự.
- Nội dung dài hơn nên chia theo câu ở nguồn. Không chia một từ thành các âm tiết độc lập.
- Tự bỏ qua file có cùng nội dung, Pinyin, giọng, tốc độ và cấu hình model. Sửa nội dung hoặc đổi giọng sẽ tạo file mới.
- Có thể dừng sau mẫu hiện tại, rồi chạy lại cùng danh sách. Mục lỗi được thử lại ở lần chạy sau.
- Thư mục `output/kokoro` và `output/melo` chứa WAV, manifest và nhật ký. Không đưa model, môi trường Python hoặc audio lên Git.
- **Bản này chưa có API lấy job từ CMS / upload R2.** Chức năng đó cần thay đổi backend và CMS, thực hiện sau khi chọn model và giọng. Danh sách JSON cho phép thử batch ngay, không cần nhập từng từ. Chưa phải hệ thống audio đã nối vào Learning app.

## Nghe và duyệt

Mỗi mẫu có **Đạt / Cần thay / Để sau**, lưu vào `manifest.json`. File mới mặc định `pending`, không tự coi là audio chuẩn. Duyệt sau khi batch đã dừng hoặc hoàn tất.

Pinyin là metadata để đối chiếu và tách cache, **không phải lệnh ép cách đọc** cho hai model. Từ đa âm phải nghe kỹ. Bộ 20 mẫu gồm bốn thanh, từ có ü/iu/ui, từ đa âm, câu tự nhiên và tên bộ thủ. Chưa có mẫu phụ âm Latin đọc riêng; không gửi `zh`, `ü`, `氵` để model đoán. Không tự lấy mẫu chưa duyệt làm đáp án luyện thanh điệu. Chất lượng cần giáo viên kiểm tra; thay bằng bản thu nếu model không phù hợp.

## Linux / macOS và CLI

```bash
python3.12 -m venv .venv-kokoro
.venv-kokoro/bin/python -m pip install -r requirements/kokoro.txt
.venv-kokoro/bin/python -m pion_audio.download
python3.12 -m pion_audio.server
```

CLI không cần mở giao diện:

```bash
.venv-kokoro/bin/python -m pion_audio.worker --engine kokoro
.venv-kokoro/bin/python -m pion_audio.worker --engine kokoro --input samples/mandarin-20.json --voice zf_001 --speed 0.85
```

Không chạy CLI và giao diện tạo batch cùng lúc vào một thư mục output. Mỗi lần tạo sẽ cập nhật bảng kết quả của model đó; file audio cũ vẫn được giữ để tái sử dụng. Nhấn Ctrl+C dừng CLI sau mục hiện tại. Trên giao diện dùng nút Dừng trước khi đóng terminal; tiến trình bị ngắt có thể tiếp tục bằng cùng lệnh/danh sách.

## Kiểm tra

```bash
python -m unittest discover -s tests -v
```

Các test dùng WAV giả lập để kiểm tra resume, cache, validation, review và HTTP local; không dùng giọng giả làm audio mẫu. Kiểm tra model thật được ghi riêng trong `VALIDATION.md`.

## Nguồn và giấy phép

- Kokoro model: https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh — Apache-2.0.
- Kokoro ONNX runtime: https://github.com/thewh1teagle/kokoro-onnx — MIT.
- Chinese G2P: https://github.com/thewh1teagle/misaki — xem giấy phép của bản cài và dependencies.
- MeloTTS: https://github.com/myshell-ai/MeloTTS — MIT; checkpoint: https://huggingface.co/myshell-ai/MeloTTS-Chinese.

Model được tải trực tiếp từ upstream, không đóng gói lại trong repo này. `models/kokoro-zh/download-receipt.json` lưu URL và SHA256 nhận được để đối chiếu; đây là hash của file tải về, không phải chữ ký xác thực độc lập. Giữ thông báo giấy phép khi phân phối lại các thành phần upstream. Chi phí API TTS bằng 0 khi tự chạy; vẫn dùng tài nguyên máy và nơi lưu/phân phối audio nếu tích hợp sau.
