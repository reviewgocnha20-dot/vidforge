# BẮP AI VIDEO

## Deploy lên Streamlit Community Cloud

1. Đưa `app.py`, `requirements.txt`, `supabase_schema.sql` lên cùng một GitHub repository.
2. Mở Supabase > SQL Editor, chạy toàn bộ `supabase_schema.sql`.
3. Trong Streamlit Cloud > App > Settings > Secrets, thêm:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_OR_PUBLISHABLE_KEY"
FAL_KEY = "YOUR_FAL_KEY"
ADMIN_EMAIL = "admin@yourdomain.com"
```

4. Trong Supabase Auth, đặt `app_metadata.admin=true` cho tài khoản admin (không đặt trong user-editable metadata).
5. Deploy app với Main file path là `app.py`.

## Chạy máy cá nhân

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Tạo `.env` cục bộ theo mẫu:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=YOUR_SUPABASE_ANON_OR_PUBLISHABLE_KEY
FAL_KEY=YOUR_FAL_KEY
ADMIN_EMAIL=admin@yourdomain.com
```

## Lưu ý quan trọng trước khi chạy thật

- Không commit `.env`, API keys hoặc service-role key lên GitHub.
- Admin cần `app_metadata.admin=true` để RPC xác nhận nạp tiền hoạt động.
- Xác minh tiền vào tài khoản ngân hàng thủ công trước khi bấm xác nhận.
- Đây là bản nền tích hợp API; cần kiểm thử với tài khoản Supabase/fal.ai thật và đối chiếu input schema, giá model, giới hạn tài khoản trước khi mở cho người dùng.
- Tạo ảnh/video hiện trừ Credits trước khi gọi API. Nếu API thất bại, cần admin đối soát và hoàn Credits thủ công; chưa có cơ chế hoàn tiền tự động.
- Edge TTS cần kết nối internet; giọng và dịch vụ có thể thay đổi theo Microsoft.
