import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader, PdfWriter
import tempfile
import os
import time

# --- Cấu hình ---
st.set_page_config(page_title="Đổi tên PDF (Final)", layout="centered")
st.title("🛡️ Đổi tên PDF (Bản Kiên Cố)")
st.write("Cơ chế kép: Cố gắng cắt nhỏ file -> Nếu thất bại sẽ Upload file gốc và CHỜ đến khi xong.")

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

# --- HÀM 2: Cắt 3 trang đầu ---
def create_lightweight_sample(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        writer = PdfWriter()
        # Lấy tối đa 3 trang
        for i in range(min(3, len(reader.pages))):
            writer.add_page(reader.pages[i])
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_sample:
            writer.write(tmp_sample)
            return tmp_sample.name, True # True = Cắt thành công
    except Exception:
        # Nếu lỗi cắt, trả về file gốc
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_full:
            uploaded_file.seek(0)
            tmp_full.write(uploaded_file.read())
            return tmp_full.name, False # False = Dùng file gốc

# --- HÀM 3: Xử lý file (Có vòng lặp chờ) ---
def process_file_final(uploaded_file, api_key, model_name):
    tmp_path = None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # 1. Tạo file (thử cắt nhỏ trước)
        tmp_path, is_cut_success = create_lightweight_sample(uploaded_file)
        
        if not is_cut_success:
            st.warning(f"⚠️ Không thể cắt nhỏ file {uploaded_file.name} (do file đặc biệt). Đang dùng file gốc, vui lòng chờ lâu hơn xíu...")

        # 2. Upload lên Google
        myfile = genai.upload_file(tmp_path, mime_type="application/pdf")
        
        # 3. VÒNG LẶP CHỜ (Bắt buộc phải có để trị file lớn)
        # Kiểm tra trạng thái file mỗi 2 giây
        while myfile.state.name == "PROCESSING":
            time.sleep(2)
            myfile = genai.get_file(myfile.name)
            
        if myfile.state.name == "FAILED":
            raise ValueError("Google không đọc được file này.")

        # 4. Prompt
        prompt = """
        Trích xuất thông tin để đặt tên file PDF này.
        Cấu trúc: YYYYMMDD_LOAI_SoHieu_NoiDung_Signed.pdf
        
        Quy tắc:
        - YYYYMMDD: Năm tháng ngày (Ví dụ 20251231).
        - LOAI: QD, TTr, CV, TB, GP, HD...
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
    uploaded_files = st.file_uploader("Chọn file PDF", type=['pdf'], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 XỬ LÝ LẦN CHỐT"):
        st.info("🤖 Đang kết nối AI...")
        active_model = get_best_model(api_key)
        
        if not active_model:
            st.error("❌ Key lỗi.")
            st.stop()
            
        st.success(f"✅ Model hoạt động: **{active_model}**")
        st.write("---")

        for i, uploaded_file in enumerate(uploaded_files):
            with st.container():
                uploaded_file.seek(0)
                st.text(f"⏳ Đang xử lý: {uploaded_file.name}...")
                
                new_name, error_msg = process_file_final(uploaded_file, api_key, active_model)
                
                if error_msg:
                    st.error(f"❌ Lỗi: {error_msg}")
                else:
                    st.success(f"✅ Xong: **{new_name}**")
                    uploaded_file.seek(0)
                    st.download_button(
                        label=f"⬇️ TẢI FILE: {new_name}",
                        data=uploaded_file,
                        file_name=new_name,
                        mime='application/pdf',
                        key=f"dl_{i}"
                    )
            st.write("---")
else:
    st.warning("👉 Nhập Key.")
