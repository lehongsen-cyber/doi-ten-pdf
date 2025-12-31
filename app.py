import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from pypdf import PdfReader
import io
import time

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(
    page_title="Smart PDF Renamer Pro",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS TÙY CHỈNH (ĐÃ FIX MÀU CHỮ) ---
st.markdown("""
<style>
    h1 {color: #2E86C1; font-family: 'Helvetica Neue', sans-serif;}
    
    /* FIX LỖI MÀU CHỮ: Ép chữ màu đen (color: #31333F) để nổi trên nền trắng */
    .result-card {
        background-color: #f8f9fa; 
        padding: 20px; 
        border-radius: 10px;
        border-left: 5px solid #28a745; 
        margin-bottom: 15px;
        color: #31333F !important; /* Quan trọng: Màu đen đè lên màu trắng của DarkMode */
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    .stButton>button {width: 100%; border-radius: 8px; height: 3em; font-weight: bold;}
    
    /* Ẩn bớt footer thừa */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- LOGIC XỬ LÝ (GIỮ NGUYÊN) ---
def get_best_model(api_key):
    genai.configure(api_key=api_key)
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name:
                return m.name
    except:
        return None
    return "models/gemini-1.5-flash"

def pdf_page_to_image(uploaded_file):
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        page = doc.load_page(0) 
        pix = page.get_pixmap(dpi=150)
        img_data = pix.tobytes("png")
        return img_data
    except Exception:
        return None

def process_with_retry(uploaded_file, api_key, model_name, status_container):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        uploaded_file.seek(0)
        img_data = pdf_page_to_image(uploaded_file)
        if img_data is None: return "ERROR", "Lỗi đọc file."

        image_part = {"mime_type": "image/png", "data": img_data}
        
        prompt = """
        Trích xuất thông tin đặt tên file PDF theo chuẩn hành chính VN.
        Cấu trúc: YYYYMMDD_LOAI_SoHieu_NoiDung_Signed.pdf
        Quy tắc:
        - YYYYMMDD: Năm tháng ngày (Ví dụ 20251231).
        - LOAI: QD, TTr, CV, TB, GP, HD, BB, BC...
        - SoHieu: Số hiệu (Ví dụ 125-UBND, thay / bằng -).
        - NoiDung: Tiếng Việt không dấu, tóm tắt, nối bằng gạch dưới (_).
        Chỉ trả về tên file.
        """
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = model.generate_content([prompt, image_part])
                new_name = result.text.strip().replace("`", "")
                if not new_name.lower().endswith(".pdf"): new_name += ".pdf"
                return new_name, None
                
            except Exception as e:
                if "429" in str(e) or "Quota" in str(e):
                    if attempt < max_retries - 1:
                        with status_container:
                            st.warning(f"⏳ Google đang bận. Đang chờ 32s để hồi phục... (Lần {attempt+1})")
                            time.sleep(32)
                            st.info("🔄 Đang thử lại...")
                            continue
                    else:
                        return None, "Google quá tải, vui lòng thử lại sau 1 phút."
                else:
                    return None, str(e)
                    
    except Exception as e:
        return None, str(e)

# --- GIAO DIỆN NGƯỜI DÙNG ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3143/3143460.png", width=80)
    st.title("Smart Renamer")
    st.markdown("---")
    with st.expander("🔑 Google API Key", expanded=True):
        api_key = st.text_input("Dán Key vào đây:", type="password")
    st.caption("Auto-Retry enabled.")

st.title("📑 HỆ THỐNG SỐ HÓA TÊN TÀI LIỆU")
# Đã xóa dòng chữ (Chống lỗi 429) theo yêu cầu
st.markdown("##### 🚀 Tự động đổi tên văn bản hành chính")

uploaded_files = st.file_uploader("", type=['pdf'], accept_multiple_files=True)

if uploaded_files:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        start_btn = st.button("✨ BẮT ĐẦU XỬ LÝ ✨", type="primary")

    if start_btn:
        if not api_key:
            st.toast("⚠️ Nhập API Key trước!", icon="⚠️")
        else:
            active_model = get_best_model(api_key)
            if not active_model:
                st.error("❌ Key không hợp lệ!")
                st.stop()
            
            st.success(f"✅ Đã kết nối: {active_model}")
            progress_bar = st.progress(0)
            
            for i, uploaded_file in enumerate(uploaded_files):
                with st.container():
                    status_box = st.empty()
                    
                    new_name, error_msg = process_with_retry(uploaded_file, api_key, active_model, status_box)
                    
                    if error_msg:
                        st.error(f"❌ {uploaded_file.name}: {error_msg}")
                    else:
                        status_box.empty()
                        
                        col_info, col_dl = st.columns([3, 1])
                        with col_info:
                            # Card UI đã sửa màu chữ
                            st.markdown(f"""
                            <div class="result-card">
                                <b>📄 Gốc:</b> {uploaded_file.name}<br>
                                <b style="color: #28a745; font-size: 1.1em;">✅ Mới:</b> {new_name}
                            </div>
                            """, unsafe_allow_html=True)
                        with col_dl:
                            st.write("")
                            st.write("")
                            uploaded_file.seek(0)
                            st.download_button(
                                label="⬇️ TẢI VỀ",
                                data=uploaded_file,
                                file_name=new_name,
                                mime='application/pdf',
                                key=f"dl_{i}",
                                use_container_width=True
                            )
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            st.balloons()
            st.success("🎉 Hoàn tất!")
