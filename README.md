# Pion Audio Tools Local

Công cụ nội bộ tạo và nghe đối chiếu audio tiếng Trung bằng **Kokoro v1.1-zh** và **MeloTTS**. Chạy trên máy của người nhập liệu, không dùng API TTS trả phí.

## Bắt đầu trên Windows — thử Kokoro trước

Các lệnh dưới đây chạy trong **Terminal của VS Code**, bằng PowerShell hoặc CMD. Chạy **từng lệnh**, chờ hoàn tất rồi mới sang lệnh tiếp theo; nếu có lỗi thì dừng tại bước đó.

### 1. Mở đúng thư mục dự án

Nếu đã clone và mở `audio-tools-local` trong VS Code, chọn **Terminal → New Terminal**, không cần clone lại. Terminal phải đang ở thư mục chứa `README.md`, `pion_audio` và `requirements`, ví dụ:

```powershell
cd C:\SPACE_WEB\audio-tools-local
```

Nếu chưa có dự án, cài [Git](https://git-scm.com/downloads/win), rồi chạy:

```powershell
git clone https://github.com/toainguyen1504/audio-tools-local.git
cd audio-tools-local
```

### 2. Kiểm tra Python đang có

```powershell
py -0p
py --version
```

- `py -0p` liệt kê các phiên bản Python và đường dẫn đã cài.
- `py --version` hoặc `python --version` hiển thị phiên bản mặc định. Không dùng `py -version` hoặc `python -v`: `-v` bật nhật ký import và mở trình Python tương tác.
- Nếu đang thấy dấu `>>>`, nhập `exit()` rồi Enter để quay lại terminal trước khi chạy các lệnh cài.

**Nếu máy đã có Python 3.11 x64, có thể dùng phiên bản này để thử Kokoro, chưa cần cài thêm Python 3.12.** Các lệnh chính bên dưới dùng 3.11. Nếu dùng Python 3.12 x64, thay các lệnh `py -3.11` bằng `py -3.12` khi kiểm tra và tạo môi trường; các lệnh gọi `.venv-kokoro` giữ nguyên.

Kiểm tra đúng phiên bản và kiến trúc:

```powershell
py -3.11 -c "import sys, struct; print(sys.version); print('Architecture:', struct.calcsize('P') * 8, 'bit')"
```

Kết quả cần có Python **3.11.x** và **64 bit**. Bản model thật trong môi trường phát triển đã được kiểm tra với Python 3.12 trên Linux; việc cài và chạy trên Windows cần kiểm tra trên máy người dùng, xem [VALIDATION.md](VALIDATION.md).

Nếu chưa có 3.11 hoặc 3.12 x64, cài một trong hai từ [python.org](https://www.python.org/downloads/windows/), chọn **Windows installer (64-bit)** và tích **Add python.exe to PATH**. Sau khi cài, mở lại VS Code và kiểm tra lại. Không dùng Python 32-bit hoặc 3.14 cho hướng dẫn này.

### 3. Tạo môi trường và cài Kokoro — làm lần đầu

Tạo môi trường riêng, không cài thư viện vào Python dùng cho dự án khác:

```powershell
py -3.11 -m venv .venv-kokoro
```

Kiểm tra môi trường vừa tạo:

```powershell
.\.venv-kokoro\Scripts\python.exe --version
```

Cài thư viện:

```powershell
.\.venv-kokoro\Scripts\python.exe -m pip install --upgrade pip
```

```powershell
.\.venv-kokoro\Scripts\python.exe -m pip install -r requirements/kokoro.txt
```

Tải model:

```powershell
.\.venv-kokoro\Scripts\python.exe -m pion_audio.download
```

Chờ đến khi hiện **“Model đã sẵn sàng”**. Lần đầu tải thư viện và khoảng 350–400 MB model/giọng/config từ upstream; cần internet và dung lượng trống cho cả thư viện lẫn model. Không cần Azure key, tài khoản Hugging Face hoặc GPU. Kokoro có thể tạo audio offline sau khi đã tải đủ dữ liệu.

Không cần chạy `Activate.ps1`; gọi trực tiếp `python.exe` của môi trường như trên giúp CMD và PowerShell đều dùng đúng Python.

### 4. Mở giao diện và nghe thử

```powershell
.\.venv-kokoro\Scripts\python.exe -m pion_audio.server
```

Trình duyệt sẽ mở **http://127.0.0.1:8765**. Nếu chưa tự mở, nhập địa chỉ đó vào trình duyệt. Không dùng Live Server để mở `web/index.html`; giao diện cần Python server để tạo và phát audio.

1. Chọn model **Kokoro**.
2. Giữ giọng **`zf_001`**, tốc độ **1.0**.
3. Nhấn **Tạo / tiếp tục 20 mẫu**.
4. Chờ xử lý xong, nghe từng file trong cột Kokoro và chọn **Đạt / Cần thay / Để sau**.

Cột MeloTTS chưa có audio là bình thường nếu chưa cài hoặc chạy model đó. Trạng thái tạo thành công chỉ xác nhận đã có file, không thay cho việc nghe duyệt phát âm.

Giữ terminal đang chạy trong lúc sử dụng. Khi cần dừng batch, bấm **Dừng sau mẫu hiện tại**, chờ hoàn tất rồi nhấn Ctrl+C tại terminal để đóng server. Nếu cổng 8765 bận:

```powershell
.\.venv-kokoro\Scripts\python.exe -m pion_audio.server --port 8766
```

Sau đó mở http://127.0.0.1:8766.

### 5. Những lần mở tiếp theo

Chỉ cần mở terminal tại thư mục dự án và chạy:

```powershell
.\.venv-kokoro\Scripts\python.exe -m pion_audio.server
```

Không cần tạo lại môi trường, cài thư viện hoặc tải model mỗi lần mở. Các file đã có được dùng lại khi nội dung, cách đọc và cấu hình không đổi.

### Lưu ý về các script có sẵn

**`scripts/setup-kokoro.ps1`, `scripts/start.ps1` và `start.cmd` hiện gọi cố định Python 3.12.** Nếu máy chỉ có 3.11, hãy dùng các lệnh trực tiếp ở trên; chưa dùng các script này. README này cập nhật hướng dẫn, không thay đổi nội dung script.

Nếu máy có Python 3.12 x64 và muốn dùng script cài:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-kokoro.ps1
```

Sau khi cài xong, vẫn có thể mở giao diện bằng lệnh `.\.venv-kokoro\Scripts\python.exe -m pion_audio.server`.

### Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `No suitable Python runtime found` | Phiên bản được gọi chưa có hoặc launcher chưa nhận. Chạy `py -0p`, dùng đúng 3.11/3.12 x64 đã cài. |
| `Unknown option` khi chạy `py -version` | Dùng `py --version` với hai dấu `-`. |
| Rất nhiều dòng `import ...`, xuất hiện `>>>` | Đã chạy `python -v`. Nhập `exit()`, rồi dùng `python --version`. |
| Không tìm thấy `.venv-kokoro\Scripts\python.exe` | Kiểm tra đang ở đúng thư mục và bước tạo môi trường đã thành công. |
| `No module named pion_audio` | Chạy từ thư mục gốc `audio-tools-local`, không từ `scripts`, `web` hoặc `pion_audio`. |
| `No module named kokoro_onnx`, `misaki` hoặc `soundfile` | Chạy lại lệnh cài `requirements/kokoro.txt` bằng đúng `.venv-kokoro\Scripts\python.exe`. |
| Báo thiếu model / chưa tải model | Chạy lại `.\.venv-kokoro\Scripts\python.exe -m pion_audio.download`. Chỉ thêm `--force` khi cần tải lại file lỗi. |
| Không mở được trang local | Giữ Python server đang chạy; kiểm tra địa chỉ và cổng được in trong terminal. |
| Batch báo lỗi | Mở **Nhật ký xử lý**, xem lỗi của mẫu. Gửi các dòng cuối log để xác định nguyên nhân, không cần gửi toàn bộ nhật ký cài đặt. |

### 6. So sánh MeloTTS (tùy chọn, sau khi Kokoro đã chạy)

MeloTTS cần môi trường riêng. Kiểm tra máy đã có **Python 3.10 x64** và **Git** trước khi chạy script dưới đây. Nếu chưa có, cài thêm; không dùng môi trường Kokoro để cài Melo.

```powershell
py -3.10 -c "import sys, struct; print(sys.version); print('Architecture:', struct.calcsize('P') * 8, 'bit')"
```

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
.venv-kokoro/bin/python -m pion_audio.server
```

CLI không cần mở giao diện:

```bash
.venv-kokoro/bin/python -m pion_audio.worker --engine kokoro
.venv-kokoro/bin/python -m pion_audio.worker --engine kokoro --input samples/mandarin-20.json --voice zf_001 --speed 0.85
```

Không chạy CLI và giao diện tạo batch cùng lúc vào một thư mục output. Mỗi lần tạo sẽ cập nhật bảng kết quả của model đó; file audio cũ vẫn được giữ để tái sử dụng. Nhấn Ctrl+C dừng CLI sau mục hiện tại. Trên giao diện dùng nút Dừng trước khi đóng terminal; tiến trình bị ngắt có thể tiếp tục bằng cùng lệnh/danh sách.

## Kiểm tra

Windows:

```powershell
.\.venv-kokoro\Scripts\python.exe -m unittest discover -s tests -v
```

Linux / macOS:

```bash
.venv-kokoro/bin/python -m unittest discover -s tests -v
```

Các test dùng WAV giả lập để kiểm tra resume, cache, validation, review và HTTP local; không dùng giọng giả làm audio mẫu. Kiểm tra model thật được ghi riêng trong `VALIDATION.md`.

## Nguồn và giấy phép

- Kokoro model: https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh — Apache-2.0.
- Kokoro ONNX runtime: https://github.com/thewh1teagle/kokoro-onnx — MIT.
- Chinese G2P: https://github.com/thewh1teagle/misaki — xem giấy phép của bản cài và dependencies.
- MeloTTS: https://github.com/myshell-ai/MeloTTS — MIT; checkpoint: https://huggingface.co/myshell-ai/MeloTTS-Chinese.

Model được tải trực tiếp từ upstream, không đóng gói lại trong repo này. `models/kokoro-zh/download-receipt.json` lưu URL và SHA256 nhận được để đối chiếu; đây là hash của file tải về, không phải chữ ký xác thực độc lập. Giữ thông báo giấy phép khi phân phối lại các thành phần upstream. Chi phí API TTS bằng 0 khi tự chạy; vẫn dùng tài nguyên máy và nơi lưu/phân phối audio nếu tích hợp sau.
