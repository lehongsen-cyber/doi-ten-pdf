import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader, PdfWriter
import tempfile
import os
import time

# --- Cấu hình ---
st.set_page_config(page_title="Đổi tên PDF (Smart Mode)", layout="centered")
st.title("⚡ Đổi tên PDF (Chế độ Cắt file thông minh)")
st.write("Tự động trích xuất 3 trang đầu để AI đọc. Xử lý file 100MB+ trong tích tắc.")

# --- Nhập Key ---
with st.expander("🔑 Cài đặt API Key", expanded=True):
    api_key = st.text_input("Nhập Google API Key:", type="password")

# --- HÀM 1: Dò tìm Model (Giữ nguyên vì đã chạy tốt) ---
def get_best_model(api_key):
    genai.configure(api_key=api_key)
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name:
                return m.name
    except:
        return None
    return "models/gemini-1.5-flash"

# --- HÀM 2: Cắt 3 trang đầu để giảm dung lượng ---
def create_lightweight_sample(uploaded_file):
    try:
        # Đọc file gốc
        reader = PdfReader(uploaded_file)
        writer = PdfWriter()
        
        # Chỉ lấy tối đa 3 trang đầu (nơi chứa số hiệu, ngày tháng)
        num_pages = min(3, len(reader.pages))
        for i in range(num_pages):
            writer.add_page(reader.pages[i])
            
        # Lưu ra một file tạm bé xíu
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_sample:
            writer.write(tmp_sample)
            return tmp_sample.name
    except Exception:
        # Nếu lỗi cắt file (hiếm gặp), thì trả về file gốc dùng tạm
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_full:
            uploaded_file.seek(0)
            tmp_full.write(uploaded_file.read())
            return tmp_full.name

# --- HÀM 3: Xử lý file ---
def process_file_smart(uploaded_file, api_key, model_name):
    tmp_path = None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # BƯỚC QUAN TRỌNG: Tạo bản mẫu nhẹ (chỉ 3 trang)
        tmp_path = create_lightweight_sample(uploaded_file)
        
        # Upload file mẫu lên Google (File này rất nhẹ nên cực nhanh)
        myfile = genai.upload_file(tmp_path, mime_type="application/pdf")
        
        # Vẫn chờ xíu cho chắc, nhưng file nhỏ thì 2s là dư xăng
        time.sleep(2)
        
        # Prompt lệnh
        prompt = """
        Đây là 3 trang đầu của một tài liệu. Hãy trích xuất thông tin để đặt tên file.
        Cấu trúc: YYYYMMDD_LOAI_SoHieu_NoiDung_Signed.pdf
        
        Quy tắc:
        - YYYYMMDD: Năm tháng ngày (Ví dụ 20251231).
        - LOAI: QD, TTr, CV, TB, GP, HD, BB, BC...
        - SoHieu: Số hiệu (Ví dụ 125-UBND, thay / bằng -).
        - NoiDung: Tiếng Việt không dấu, nối bằng gạch dưới (_).
        
        Chỉ trả về duy nhất tên file kết quả.
        """
        
        result = model.generate_content([myfile, prompt])
        new_name = result.text.strip().replace("`", "")
        if not new_name.lower().endswith(".pdf"):
            new_name += ".pdf"
            
        return new_name, None
        
    except Exception as e:
        return None, str(e)
    finally:
        # Dọn dẹp file rác
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- Giao diện ---
if api_key:
    uploaded_files = st.file_uploader("Chọn file PDF (Bao cân file nặng)", type=['pdf'], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 Xử lý ngay"):
        st.info("🤖 Đang kết nối AI...")
        active_model = get_best_model(api_key)
        
        if not active_model:
            st.error("❌ Key lỗi hoặc không tìm thấy model.")
            st.stop()
            
        st.success(f"✅ Đang dùng model: **{active_model}**")
        st.write("---")

        for i, uploaded_file in enumerate(uploaded_files):
            with st.container():
                # Reset con trỏ file về đầu
                uploaded_file.seek(0)
                st.text(f"⏳ Đang xử lý: {uploaded_file.name}...")
                
                # Gọi hàm xử lý thông minh
                new_name, error_msg = process_file_smart(uploaded_file, api_key, active_model)
                
                if error_msg:
                    st.error(f"❌ Lỗi: {error_msg}")
                else:
                    st.success(f"✅ Xong: **{new_name}**")
                    
                    # Quan trọng: Nút tải về vẫn chứa nội dung FILE GỐC (Full)
                    uploaded_file.seek(0)
                    st.download_button(
                        label=f"⬇️ TẢI FILE GỐC ĐÃ ĐỔI TÊN",
                        data=uploaded_file,
                        file_name=new_name,
                        mime='application/pdf',
                        key=f"dl_{i}"
                    )
            st.write("---")
else:
    st.warning("👉 Nhập Key để bắt đầu.")
