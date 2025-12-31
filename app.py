import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

# --- Cấu hình ---
st.set_page_config(page_title="Đổi tên PDF (Signed Fix)", layout="centered")
st.title("💎 Đổi tên PDF (Chuyên trị File Ký Số)")
st.write("Chế độ an toàn: Upload nguyên bản & Chờ xử lý. Không làm hỏng chữ ký số.")

# --- Nhập Key ---
with st.expander("🔑 Cài đặt API Key", expanded=True):
    api_key = st.text_input("Nhập Google API Key:", type="password")

# --- HÀM 1: Dò tìm Model ---
def get_best_model(api_key):
    genai.configure(api_key=api_key)
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name:
                return m.name
    except:
        return None
    return "models/gemini-1.5-flash"

# --- HÀM 2: Xử lý file (Không cắt - Chờ Active) ---
def process_signed_pdf(uploaded_file, api_key, model_name):
    tmp_path = None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # 1. Lưu file tạm (Nguyên vẹn)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        # 2. Upload lên Google
        # Tạo placeholder để hiện thông báo trạng thái
        status_box = st.empty()
        status_box.info("☁️ Đang upload file 58MB lên Google (Mất khoảng 5-10s)...")
        
        myfile = genai.upload_file(tmp_path, mime_type="application/pdf")
        
        # 3. VÒNG LẶP CHỜ (QUAN TRỌNG NHẤT)
        # File 58MB cần khoảng 20-30 giây để Google 'nuốt'
        wait_time = 0
        while myfile.state.name == "PROCESSING":
            status_box.warning(f"⏳ Google đang đọc file... (Đã chờ {wait_time}s). Vui lòng KHÔNG tắt tab.")
            time.sleep(5)
            wait_time += 5
            myfile = genai.get_file(myfile.name)
            
        if myfile.state.name == "FAILED":
            raise ValueError("Google báo lỗi: File bị hỏng hoặc format lạ.")

        status_box.success("✅ Google đã đọc xong! Đang phân tích tên...")

        # 4. Prompt
        prompt = """
        Đây là văn bản hành chính Việt Nam. Hãy trích xuất thông tin để đặt tên file.
        Cấu trúc: YYYYMMDD_LOAI_SoHieu_NoiDung_Signed.pdf
        
        Quy tắc:
        - YYYYMMDD: Năm tháng ngày ban hành (Ví dụ 20251231).
        - LOAI: QD, TTr, CV, TB, GP, HD, BB, BC...
        - SoHieu: Số hiệu (Ví dụ 125-UBND, thay / bằng -).
        - NoiDung: Tiếng Việt không dấu, nối bằng gạch dưới (_).
        
        Chỉ trả về tên file.
        """
        
        result = model.generate_content([myfile, prompt])
        new_name = result.text.strip().replace("`", "")
        if not new_name.lower().endswith(".pdf"):
            new_name += ".pdf"
            
        return new_name, None
        
    except Exception as e:
        return None, str(e)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- Giao diện ---
if api_key:
    uploaded_files = st.file_uploader("Chọn file PDF (Signed/Scan/File Lớn)", type=['pdf'], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 XỬ LÝ"):
        active_model = get_best_model(api_key)
        if not active_model:
            st.error("❌ Key lỗi.")
            st.stop()
        
        st.caption(f"🤖 Model: {active_model}")
        st.write("---")

        for i, uploaded_file in enumerate(uploaded_files):
            with st.container():
                st.text(f"📄 File: {uploaded_file.name}")
                
                new_name, error_msg = process_signed_pdf(uploaded_file, api_key, active_model)
                
                if error_msg:
                    st.error(f"❌ Lỗi: {error_msg}")
                else:
                    st.success(f"✅ Xong: **{new_name}**")
                    uploaded_file.seek(0)
                    st.download_button(
                        label=f"⬇️ TẢI VỀ: {new_name}",
                        data=uploaded_file,
                        file_name=new_name,
                        mime='application/pdf',
                        key=f"dl_{i}"
                    )
            st.write("---")
else:
    st.warning("👉 Nhập Key.")
