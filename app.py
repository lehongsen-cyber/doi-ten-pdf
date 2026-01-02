import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import io
import time
import os
import zipfile

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(
    page_title="Smart Renamer - Group PTDA",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS TÙY CHỈNH ---
st.markdown("""
<style>
    h1 {color: #2E86C1; font-family: 'Helvetica Neue', sans-serif;}
    
    .result-card {
        background-color: #f8f9fa; 
        padding: 20px; 
        border-radius: 10px;
        border-left: 5px solid #28a745; 
        margin-bottom: 15px;
        color: #31333F !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    .stButton>button {width: 100%; border-radius: 8px; height: 3em; font-weight: bold;}
    
    /* Căn giữa ảnh trong Sidebar */
    [data-testid="stSidebar"] img {
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
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
        
        # --- QUY TẮC CŨ CỦA NHÓM PTDA (YYYYMMDD) ---
        prompt = """
        Trích xuất thông tin đặt tên file PDF theo chuẩn hành chính VN.
        Cấu trúc: YYYYMMDD_LOAI_SoHieu_NoiDung_TrangThai.pdf
        Quy tắc:
        - YYYYMMDD: Năm tháng ngày (Ví dụ: 20251231). Viết liền 8 số.
        - LOAI: QD, TTr, CV, TB, GP, HD, BB, BC...
        - SoHieu: Số hiệu (Ví dụ 125-UBND, thay / bằng -).
        - NoiDung: Tiếng Việt không dấu, tóm tắt, nối bằng gạch dưới (_).
        - TrangThai: Mặc định 'Signed'.
        Chỉ trả về tên file.
        """
        
        max_retries = 5
        wait_time = 65
        
        for attempt in range(max_retries):
            try:
                result = model.generate_content([prompt, image_part])
                new_name = result.text.strip().replace("`", "")
                if not new_name.lower().endswith(".pdf"): new_name += ".pdf"
                return new_name, None
                
            except Exception as e:
                if "429" in str(e) or "Quota" in str(e) or "400" in str(e):
                    if attempt < max_retries - 1:
                        with status_container:
                            for s in range(wait_time, 0, -1):
                                st.warning(f"⏳ Google đang quá tải. Vui lòng chờ {s} giây... (Lần {attempt+1})")
                                time.sleep(1)
                            st.info("🔄 Đang kết nối lại...")
                            continue
                    else:
                        return None, "Google quá tải quá lâu. Vui lòng thử lại vào ngày mai."
                else:
                    return None, str(e)
                    
    except Exception as e:
        return None, str(e)

# --- GIAO DIỆN NGƯỜI DÙNG ---
with st.sidebar:
    # 1. LOGO
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=120)
    
    st.title("Smart Renamer")
    st.markdown("---")
    
    with st.expander("🔑 Google API Key", expanded=True):
        api_key = st.text_input("Dán Key vào đây:", type="password")
    
    st.caption("✅ Auto-Retry enabled.")
    st.markdown("---")
    
    # 2. QR CODE & CREDITS
    st.markdown("<h4 style='text-align: center;'>Tham gia cộng đồng</h4>", unsafe_allow_html=True)
    if os.path.exists("qr.jpg"):
        st.image("qr.jpg", use_container_width=True)
    
    st.markdown("""
    <div style="text-align: center; margin-top: 10px; font-size: 0.8em; color: gray;">
        <b>Created by Anh em Phát triển Dự án Miền Nam</b>
    </div>
    """, unsafe_allow_html=True)

# --- PHẦN CHÍNH ---
st.title("📑 HỆ THỐNG SỐ HÓA TÊN TÀI LIỆU")
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
            
            # Danh sách để nén ZIP
            success_files = []
            
            for i, uploaded_file in enumerate(uploaded_files):
                with st.container():
                    status_box = st.empty()
                    
                    new_name, error_msg = process_with_retry(uploaded_file, api_key, active_model, status_box)
                    
                    if error_msg:
                        st.error(f"❌ {uploaded_file.name}: {error_msg}")
                    else:
                        status_box.empty()
                        
                        # Lưu file vào bộ nhớ đệm
                        uploaded_file.seek(0)
                        file_data = uploaded_file.read()
                        success_files.append((new_name, file_data))
                        
                        col_info, col_dl = st.columns([3, 1])
                        with col_info:
                            st.markdown(f"""
                            <div class="result-card">
                                <b>📄 Gốc:</b> {uploaded_file.name}<br>
                                <b style="color: #28a745; font-size: 1.1em;">✅ Mới:</b> {new_name}
                            </div>
                            """, unsafe_allow_html=True)
                        with col_dl:
                            st.write("")
                            # Nút tải lẻ
                            st.download_button(
                                label="⬇️ Tải lẻ",
                                data=file_data,
                                file_name=new_name,
                                mime='application/pdf',
                                key=f"dl_{i}",
                                use_container_width=True
                            )
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            # --- TẠO NÚT TẢI ZIP ---
            if success_files:
                st.markdown("---")
                st.success("🎉 Xử lý xong! Bấm nút dưới để tải tất cả mà KHÔNG bị reload trang.")
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for name, data in success_files:
                        zf.writestr(name, data)
                
                st.download_button(
                    label="📦 TẢI VỀ TẤT CẢ (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="Ho_so_da_doi_ten.zip",
                    mime="application/zip",
                    type="primary",
                    use_container_width=True
                )
