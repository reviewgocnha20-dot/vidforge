# -*- coding: utf-8 -*-
"""BẮP AI VIDEO — Streamlit starter app.
Secrets required: SUPABASE_URL, SUPABASE_KEY (anon/publishable key),
FAL_KEY, ADMIN_EMAIL. Never put service-role keys in a public repository.
"""
import os
import asyncio
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client
import fal_client
import edge_tts

load_dotenv()

st.set_page_config(page_title="BẮP AI VIDEO", page_icon="🎬", layout="wide")

def get_env(key: str, default: str = "") -> str:
    try:
        value = st.secrets.get(key, "")
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(key, default)

SUPABASE_URL = get_env("SUPABASE_URL")
SUPABASE_KEY = get_env("SUPABASE_KEY")
FAL_KEY = get_env("FAL_KEY")
ADMIN_EMAIL = get_env("ADMIN_EMAIL", "admin@bapaivideo.com").lower()

COST_IMAGE_EDIT = 2
COST_VIDEO_GEN = 10
BANK_INFO = {
    "bank_code": "PVCB",
    "bank_bin": "970412",
    "bank_name": "PVcomBank",
    "account_number": "107004099152",
    "account_name_ascii": "NGO VAN KHANH",
}
CREDIT_PACKAGES = [
    {"id": "starter", "name": "Gói Cơ Bản", "amount": 50000, "credits": 50,
     "badge": "TIẾT KIỆM", "description": "Dành cho trải nghiệm tạo ảnh và video ngắn."},
    {"id": "pro", "name": "Gói Pro", "amount": 199000, "credits": 250,
     "badge": "PHỔ BIẾN NHẤT", "description": "Phù hợp nhà sáng tạo nội dung và bán hàng."},
    {"id": "studio", "name": "Gói Studio", "amount": 499000, "credits": 700,
     "badge": "SIÊU ƯU ĐÃI", "description": "Dành cho agency và sản xuất số lượng lớn."},
]
VOICES = {
    "Nữ miền Nam — Hoài My": "vi-VN-HoaiMyNeural",
    "Nam miền Bắc — Nam Minh": "vi-VN-NamMinhNeural",
}

def build_transfer_content(user_id: str, tx_id: str) -> str:
    return f"BAPAI {user_id.replace('-', '')[:4].upper()} {tx_id.replace('-', '')[:4].upper()}"

def build_vietqr_url(amount: int, add_info: str) -> str:
    bank = BANK_INFO["bank_code"]
    stk = BANK_INFO["account_number"]
    name = quote(BANK_INFO["account_name_ascii"])
    info = quote(add_info)
    return f"https://img.vietqr.io/image/{bank}-{stk}-compact2.png?amount={amount}&addInfo={info}&accountName={name}"

@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Thiếu SUPABASE_URL hoặc SUPABASE_KEY trong Secrets.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def current_user():
    return st.session_state.get("user")

def rpc(name, params):
    return get_supabase().rpc(name, params).execute().data

def refresh_profile():
    user = current_user()
    if not user:
        return None
    rows = (get_supabase().table("profiles").select("*")
            .eq("id", user.id).limit(1).execute().data)
    return rows[0] if rows else None

def sign_out():
    st.session_state.pop("user", None)
    st.session_state.pop("profile", None)
    st.rerun()

def auth_panel():
    st.title("🎬 BẮP AI VIDEO")
    st.caption("Sáng tạo hình ảnh, video và giọng đọc bằng AI")
    login_tab, signup_tab = st.tabs(["Đăng nhập", "Tạo tài khoản"])
    sb = get_supabase()
    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Mật khẩu", type="password", key="login_password")
            submitted = st.form_submit_button("Đăng nhập", use_container_width=True)
        if submitted:
            try:
                result = sb.auth.sign_in_with_password({"email": email.strip(), "password": password})
                st.session_state.user = result.user
                st.rerun()
            except Exception as exc:
                st.error(f"Đăng nhập không thành công: {exc}")
    with signup_tab:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Mật khẩu (ít nhất 8 ký tự)", type="password", key="signup_password")
            submitted = st.form_submit_button("Tạo tài khoản", use_container_width=True)
        if submitted:
            if len(password) < 8:
                st.warning("Mật khẩu cần ít nhất 8 ký tự.")
            else:
                try:
                    result = sb.auth.sign_up({"email": email.strip(), "password": password})
                    if result.session:
                        st.session_state.user = result.user
                        st.success("Tạo tài khoản thành công.")
                        st.rerun()
                    else:
                        st.success("Đã gửi email xác nhận. Hãy xác nhận email rồi đăng nhập.")
                except Exception as exc:
                    st.error(f"Không thể tạo tài khoản: {exc}")

def require_fal():
    if not FAL_KEY:
        st.error("Chưa cấu hình FAL_KEY trong Streamlit Secrets.")
        return False
    os.environ["FAL_KEY"] = FAL_KEY
    return True

def upload_to_fal(uploaded_file):
    return fal_client.upload(uploaded_file.getvalue(), content_type=uploaded_file.type)

def image_workspace():
    st.subheader("🖼️ Tạo / chỉnh sửa ảnh — FLUX Kontext")
    st.caption(f"Mỗi lượt chỉnh sửa trừ {COST_IMAGE_EDIT} Credits. Ảnh đầu vào sẽ được tải lên fal.ai để xử lý.")
    source = st.file_uploader("Ảnh cần chỉnh sửa", type=["png", "jpg", "jpeg", "webp"], key="edit_image")
    prompt = st.text_area("Mô tả thay đổi", placeholder="Ví dụ: Đổi nền thành studio trắng, giữ nguyên sản phẩm và logo.")
    if st.button("✨ Chỉnh sửa ảnh", type="primary", disabled=not (source and prompt.strip())):
        if not require_fal():
            return
        try:
            with st.spinner("Đang kiểm tra Credits..."):
                rpc("spend_credits", {"p_amount": COST_IMAGE_EDIT, "p_reason": "FLUX Kontext"})
            with st.spinner("AI đang chỉnh sửa ảnh..."):
                image_url = upload_to_fal(source)
                result = fal_client.subscribe(
                    "fal-ai/flux-pro/kontext",
                    arguments={"prompt": prompt.strip(), "image_url": image_url, "num_images": 1},
                )
            images = result.get("images", [])
            if not images:
                raise RuntimeError(f"fal.ai không trả về ảnh: {result}")
            st.image(images[0]["url"], caption="Ảnh đã tạo", use_container_width=True)
            st.markdown(f"[Mở ảnh kết quả]({images[0]['url']})")
            st.success("Hoàn tất.")
        except Exception as exc:
            st.error(f"Tạo ảnh thất bại: {exc}")
            st.info("Nếu Credits đã bị trừ nhưng API lỗi, liên hệ quản trị viên để đối soát.")

def video_workspace():
    st.subheader("🎥 Tạo video — Kling 3.0")
    st.caption(f"Mỗi lượt tạo video trừ {COST_VIDEO_GEN} Credits. Endpoint Kling V3 Standard.")
    source = st.file_uploader("Ảnh bắt đầu video", type=["png", "jpg", "jpeg", "webp"], key="video_image")
    prompt = st.text_area("Mô tả chuyển động", placeholder="Ví dụ: Máy quay tiến chậm, sản phẩm xoay nhẹ, ánh sáng studio.")
    duration = st.selectbox("Thời lượng", ["5", "10", "15"], index=0)
    if st.button("🎬 Tạo video", type="primary", disabled=not (source and prompt.strip())):
        if not require_fal():
            return
        try:
            with st.spinner("Đang kiểm tra Credits..."):
                rpc("spend_credits", {"p_amount": COST_VIDEO_GEN, "p_reason": "Kling 3.0"})
            with st.spinner("Kling 3.0 đang tạo video. Quá trình có thể mất vài phút..."):
                image_url = upload_to_fal(source)
                result = fal_client.subscribe(
                    "fal-ai/kling-video/v3/standard/image-to-video",
                    arguments={
                        "image_url": image_url,
                        "prompt": prompt.strip(),
                        "duration": duration,
                    },
                )
            video = result.get("video", {}).get("url")
            if not video:
                raise RuntimeError(f"fal.ai không trả về video: {result}")
            st.video(video)
            st.markdown(f"[Mở video kết quả]({video})")
            st.success("Hoàn tất.")
        except Exception as exc:
            st.error(f"Tạo video thất bại: {exc}")
            st.info("Nếu Credits đã bị trừ nhưng API lỗi, liên hệ quản trị viên để đối soát.")

def tts_workspace():
    st.subheader("🎙️ Giọng đọc tiếng Việt — Edge TTS")
    text = st.text_area("Nội dung cần đọc", height=160)
    voice_label = st.selectbox("Giọng đọc", list(VOICES))
    rate = st.select_slider("Tốc độ", options=["-20%", "-10%", "+0%", "+10%", "+20%"], value="+0%")
    if st.button("Tạo giọng đọc", disabled=not text.strip()):
        try:
            async def make_audio():
                communicate = edge_tts.Communicate(text.strip(), VOICES[voice_label], rate=rate)
                chunks = []
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        chunks.append(chunk["data"])
                return b"".join(chunks)
            audio = asyncio.run(make_audio())
            if audio:
                st.audio(audio, format="audio/mpeg")
                st.download_button("⬇️ Tải MP3", audio, "bap_ai_voice.mp3", "audio/mpeg")
            else:
                st.error("Không nhận được dữ liệu âm thanh.")
        except Exception as exc:
            st.error(f"Không tạo được giọng đọc: {exc}")

def topup_workspace(user):
    st.subheader("💳 Nạp Credits qua VietQR")
    st.warning("Chuyển khoản đúng số tiền và nội dung. Credits chỉ được cộng sau khi admin xác nhận.")
    for package in CREDIT_PACKAGES:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.markdown(f"**{package['name']}** · {package['badge']}")
            c1.caption(package["description"])
            c2.markdown(f"**{package['amount']:,}đ**")
            c2.write(f"{package['credits']} Credits")
            if c3.button("Chọn gói", key=f"buy_{package['id']}"):
                try:
                    tx_id = str(uuid.uuid4())
                    content = build_transfer_content(user.id, tx_id)
                    get_supabase().table("topups").insert({
                        "id": tx_id, "user_id": user.id, "package_id": package["id"],
                        "amount_vnd": package["amount"], "credits": package["credits"],
                        "transfer_content": content, "status": "pending",
                    }).execute()
                    st.session_state["active_topup"] = {
                        "id": tx_id, "amount": package["amount"], "content": content
                    }
                except Exception as exc:
                    st.error(f"Không tạo được yêu cầu nạp: {exc}")
    pending = st.session_state.get("active_topup")
    if pending:
        st.divider()
        st.markdown("**Thông tin chuyển khoản**")
        st.image(build_vietqr_url(pending["amount"], pending["content"]), width=300)
        st.write(f"Ngân hàng: {BANK_INFO['bank_name']}")
        st.write(f"Số tài khoản: {BANK_INFO['account_number']}")
        st.write(f"Chủ tài khoản: {BANK_INFO['account_name_ascii']}")
        st.code(pending["content"])
        st.caption("Không sửa nội dung chuyển khoản. Sau khi chuyển, chờ admin xác nhận.")

def history_workspace(user):
    st.subheader("📜 Lịch sử nạp Credits")
    try:
        rows = (get_supabase().table("topups").select("created_at,amount_vnd,credits,status,transfer_content")
                .eq("user_id", user.id).order("created_at", desc=True).limit(30).execute().data)
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có giao dịch.")
    except Exception as exc:
        st.error(f"Không tải được lịch sử: {exc}")

def admin_workspace():
    st.subheader("🛡️ Quản trị — xác nhận nạp Credits")
    st.caption("Chỉ tài khoản có email trùng ADMIN_EMAIL mới thấy khu vực này.")
    try:
        rows = (get_supabase().table("topups").select("*").eq("status", "pending")
                .order("created_at", desc=False).limit(100).execute().data)
        if not rows:
            st.info("Không có yêu cầu đang chờ.")
        for item in rows:
            with st.container(border=True):
                st.write(f"**{item['amount_vnd']:,}đ · {item['credits']} Credits**")
                st.write(f"User ID: `{item['user_id']}`")
                st.code(item["transfer_content"])
                if st.button("Xác nhận đã nhận tiền", key=f"approve_{item['id']}"):
                    try:
                        rpc("admin_approve_topup", {"p_topup_id": item["id"]})
                        st.success("Đã xác nhận và cộng Credits.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Không xác nhận được: {exc}")
    except Exception as exc:
        st.error(f"Không tải được yêu cầu nạp: {exc}")

def main():
    st.markdown("""
    <style>
    .stApp {background: linear-gradient(135deg, #0b1020 0%, #111a30 100%);}
    h1,h2,h3,p,label {color: inherit;}
    [data-testid="stMetric"] {background:rgba(255,255,255,.06);padding:14px;border-radius:12px;}
    </style>
    """, unsafe_allow_html=True)
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.title("🎬 BẮP AI VIDEO")
        st.error("Chưa cấu hình Supabase. Hãy thêm SUPABASE_URL và SUPABASE_KEY vào Streamlit Secrets.")
        st.stop()
    if not current_user():
        auth_panel()
        return
    user = current_user()
    try:
        profile = refresh_profile()
        if not profile:
            st.error("Không tìm thấy hồ sơ người dùng. Hãy chạy file supabase_schema.sql trong Supabase SQL Editor.")
            if st.button("Đăng xuất"):
                sign_out()
            return
        st.session_state.profile = profile
    except Exception as exc:
        st.error(f"Không tải được hồ sơ: {exc}")
        st.stop()

    with st.sidebar:
        st.title("🎬 BẮP AI VIDEO")
        st.write(user.email)
        st.metric("Số dư Credits", profile.get("credits", 0))
        st.caption("Ảnh: 2 Credits · Video: 10 Credits")
        if st.button("Đăng xuất", use_container_width=True):
            sign_out()
        st.divider()
        page = st.radio("MENU", ["Tổng quan", "Chỉnh sửa ảnh", "Tạo video", "Giọng đọc AI", "Nạp Credits", "Lịch sử giao dịch"])

    st.title("Xin chào! 👋")
    st.caption("Không gian sáng tạo nội dung bằng AI")
    if page == "Tổng quan":
        c1, c2, c3 = st.columns(3)
        c1.metric("Credits hiện có", profile.get("credits", 0))
        c2.metric("Chi phí chỉnh ảnh", f"{COST_IMAGE_EDIT} Credits")
        c3.metric("Chi phí tạo video", f"{COST_VIDEO_GEN} Credits")
        st.info("Chọn chức năng ở thanh bên để bắt đầu sáng tạo.")
        st.markdown("**BẮP AI VIDEO** · FLUX Kontext · Kling 3.0 · Edge TTS")
    elif page == "Chỉnh sửa ảnh":
        image_workspace()
    elif page == "Tạo video":
        video_workspace()
    elif page == "Giọng đọc AI":
        tts_workspace()
    elif page == "Nạp Credits":
        topup_workspace(user)
    elif page == "Lịch sử giao dịch":
        history_workspace(user)

    if (user.email or "").lower() == ADMIN_EMAIL:
        with st.sidebar:
            st.divider()
            if st.button("Mở quản trị"):
                st.session_state["show_admin"] = True
    if st.session_state.get("show_admin") and (user.email or "").lower() == ADMIN_EMAIL:
        admin_workspace()

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        st.error(f"Ứng dụng gặp lỗi: {error}")
