import streamlit as st
import google.generativeai as genai
import fitz  # Đây là thư viện PyMuPDF (Máy ảnh)
from pypdf import PdfReader
import io

# --- Cấu hình ---
st.set_page_config(page_title="Đổi tên PDF (Snapshot)", layout="centered")
st.title("📸 Đổi tên PDF (Công nghệ Chụp Ảnh)")
st.write("Giải pháp cuối: Biến file PDF thành Ảnh để lách qua mọi lỗi chữ ký số/file nặng.")

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

# --- HÀM 2: Chụp ảnh trang đầu PDF ---
def pdf_page_to_image(uploaded_file):
    try:
        # Đọc file PDF từ bộ nhớ
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        # Lấy trang đầu tiên (trang 0)
        page = doc.load_page(0) 
        # Chụp ảnh (Render thành Pixmap)
        pix = page.get_pixmap(dpi=150) # DPI 150 là đủ nét mà nhẹ
        # Chuyển thành dữ liệu ảnh PNG
        img_data = pix.tobytes("png")
        return img_data
    except Exception as e:
        return None

# --- HÀM 3: Xử lý ---
def process_with_snapshot(uploaded_file, api_key, model_name):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # 1. Reset file và chụp ảnh
        uploaded_file.seek(0)
        img_data = pdf_page_to_image(uploaded_file)
        
        if img_data is None:
            return "ERROR", "Không thể chụp ảnh file này (File lỗi hoặc mật khẩu)."

        # 2. Tạo đối tượng ảnh để gửi cho Gemini
        # Gemini nhận diện ảnh cực tốt, không quan tâm file gốc là gì
        image_part = {"mime_type": "image/png", "data": img_data}

        # 3. Prompt
        prompt = """
        Hãy nhìn bức ảnh văn bản này và trích xuất thông tin để đặt tên file.
        Cấu trúc: YYYYMMDD_LOAI_SoHieu_NoiDung_Signed.pdf
        
        Quy tắc:
        - YYYYMMDD: Năm tháng ngày (Ví dụ 20251231).
        - LOAI: QD, TTr, CV, TB, GP, HD...
        - SoHieu: Số hiệu (Ví dụ 125-UBND, thay / bằng -).
        - NoiDung: Tiếng Việt không dấu, nối bằng gạch dưới (_).
        
        Chỉ trả về tên file.
        """
        
        # 4. Gửi Ảnh + Lệnh cho AI
        result = model.generate_content([prompt, image_part])
        new_name = result.text.strip().replace("`", "")
        if not new_name.lower().endswith(".pdf"):
            new_name += ".pdf"
            
        return new_name, None
        
    except Exception as e:
        return None, str(e)

# --- Giao diện ---
if api_key:
    uploaded_files = st.file_uploader("Chọn file PDF", type=['pdf'], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 CHỤP VÀ XỬ LÝ"):
        st.info("🤖 Đang kết nối AI...")
        active_model = get_best_model(api_key)
        if not active_model:
            st.error("❌ Key lỗi.")
            st.stop()
        st.success(f"✅ Model: {active_model}")
        st.write("---")

        for i, uploaded_file in enumerate(uploaded_files):
            with st.container():
                st.text(f"📸 Đang chụp ảnh trang đầu file: {uploaded_file.name}...")
                
                # Gọi hàm xử lý ảnh
                new_name, error_msg = process_with_snapshot(uploaded_file, api_key, active_model)
                
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
