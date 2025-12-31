import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from pypdf import PdfReader
import io

# --- CẤU HÌNH GIAO DIỆN (Widescreen + Icon) ---
st.set_page_config(
    page_title="Smart PDF Renamer Pro",
    page_icon="📑",
    layout="wide", # Chế độ màn hình rộng
    initial_sidebar_state="expanded"
)

# --- CSS TÙY CHỈNH (Cho giao diện đẹp hơn) ---
st.markdown("""
<style>
    /* Chỉnh font chữ và tiêu đề */
    h1 {
        color: #2E86C1;
        font-family: 'Helvetica Neue', sans-serif;
    }
    /* Tạo khung viền (Card) cho từng file kết quả */
    .result-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #28a745;
        margin-bottom: 15px;
    }
    /* Chỉnh nút bấm to đẹp */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    /* Ẩn menu mặc định của Streamlit cho giống App riêng */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- LOGIC XỬ LÝ (GIỮ NGUYÊN CÁI ĐANG CHẠY NGON) ---
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

def process_with_snapshot(uploaded_file, api_key, model_name):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        uploaded_file.seek(0)
        img_data = pdf_page_to_image(uploaded_file)
        
        if img_data is None:
            return "ERROR", "Không thể chụp ảnh file (File lỗi)."

        image_part = {"mime_type": "image/png", "data": img_data}

        prompt = """
        Trích xuất thông tin để đặt tên file PDF này theo chuẩn hành chính Việt Nam.
        Cấu trúc: YYYYMMDD_LOAI_SoHieu_NoiDung_Signed.pdf
        
        Quy tắc:
        - YYYYMMDD: Năm tháng ngày (Ví dụ 20251231).
        - LOAI: QD, TTr, CV, TB, GP, HD, BB, BC...
        - SoHieu: Số hiệu (Ví dụ 125-UBND, thay / bằng -).
        - NoiDung: Tiếng Việt không dấu, tóm tắt ngắn gọn, nối bằng gạch dưới (_).
        
        Chỉ trả về tên file.
        """
        
        result = model.generate_content([prompt, image_part])
        new_name = result.text.strip().replace("`", "")
        if not new_name.lower().endswith(".pdf"):
            new_name += ".pdf"
            
        return new_name, None
        
    except Exception as e:
        return None, str(e)

# --- GIAO DIỆN NGƯỜI DÙNG (UI) ---

# 1. SIDEBAR (Thanh bên trái)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3143/3143460.png", width=80)
    st.title("Cấu Hình Hệ Thống")
    st.markdown("---")
    
    with st.expander("🔑 Google API Key", expanded=True):
        api_key = st.text_input("Dán Key vào đây:", type="password", help="Key giúp AI hoạt động")
        st.caption("[Lấy API Key miễn phí tại đây](https://aistudio.google.com/app/apikey)")
    
    st.info("💡 **Mẹo:** App dùng công nghệ chụp ảnh nên xử lý được mọi loại file (Scan, Ký số, File nặng).")
    st.markdown("---")
    st.caption("Developed by Gemini & You")

# 2. MAIN AREA (Khu vực chính)
st.title("📑 HỆ THỐNG SỐ HÓA TÊN TÀI LIỆU")
st.markdown("##### 🚀 Tự động đổi tên văn bản hành chính bằng AI (Công nghệ Vision)")

# Upload file
uploaded_files = st.file_uploader("", type=['pdf'], accept_multiple_files=True, help="Kéo thả file vào đây")

# Nút xử lý
if uploaded_files:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        start_btn = st.button("✨ BẮT ĐẦU XỬ LÝ NGAY ✨", type="primary")

    if start_btn:
        if not api_key:
            st.toast("⚠️ Vui lòng nhập API Key bên thanh trái trước!", icon="⚠️")
        else:
            # Tìm model
            with st.status("🤖 Đang khởi động AI...", expanded=True) as status:
                active_model = get_best_model(api_key)
                if not active_model:
                    status.update(label="❌ API Key không hợp lệ!", state="error")
                    st.stop()
                status.update(label=f"✅ Đã kết nối: {active_model}", state="complete", expanded=False)

            st.write("---")
            
            # Thanh tiến trình
            progress_bar = st.progress(0)
            
            # Xử lý từng file và hiện Card
            for i, uploaded_file in enumerate(uploaded_files):
                # Layout chia đôi: Bên trái tên cũ, Bên phải kết quả
                
                with st.container():
                    # Gọi hàm xử lý
                    new_name, error_msg = process_with_snapshot(uploaded_file, api_key, active_model)
                    
                    if error_msg:
                        st.error(f"❌ {uploaded_file.name}: {error_msg}")
                    else:
                        # Giao diện Card đẹp
                        col_info, col_dl = st.columns([3, 1])
                        
                        with col_info:
                            st.markdown(f"""
                            <div class="result-card">
                                <b>📄 Tên gốc:</b> {uploaded_file.name}<br>
                                <b style="color: green; font-size: 1.1em;">✅ Tên mới:</b> {new_name}
                            </div>
                            """, unsafe_allow_html=True)
                            
                        with col_dl:
                            # Nút download căn giữa
                            st.write("") # Spacer
                            st.write("") # Spacer
                            uploaded_file.seek(0)
                            st.download_button(
                                label="⬇️ TẢI VỀ",
                                data=uploaded_file,
                                file_name=new_name,
                                mime='application/pdf',
                                key=f"dl_{i}",
                                use_container_width=True
                            )
                
                # Update progress
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            st.balloons() # Pháo hoa chúc mừng khi xong hết
            st.success("🎉 Đã xử lý xong tất cả hồ sơ!")

else:
    # Màn hình chờ đẹp mắt khi chưa chọn file
    st.markdown("""
    <div style="text-align: center; color: gray; padding: 50px;">
        <h3>👋 Chào bạn!</h3>
        <p>Vui lòng upload file PDF để bắt đầu.</p>
    </div>
    """, unsafe_allow_html=True)
