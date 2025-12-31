import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

# --- Cấu hình ---
st.set_page_config(page_title="Đổi tên PDF Final", layout="centered")
st.title("🔥 Đổi tên PDF (Bản Final Fix)")
st.write("Tự động dò tìm Model + Đọc file Scan bằng Mắt thần.")

# --- Nhập Key ---
with st.expander("🔑 Cài đặt API Key", expanded=True):
    api_key = st.text_input("Nhập Google API Key:", type="password")

# --- HÀM 1: Dò tìm xem Key của bạn dùng được con AI nào ---
def get_best_model(api_key):
    genai.configure(api_key=api_key)
    try:
        # Lấy danh sách model mà Key này được phép dùng
        for m in genai.list_models():
            # Ưu tiên tìm mấy con đời mới flash hoặc pro
            if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name:
                return m.name # Trả về ngay cái tên đầu tiên tìm được (VD: gemini-2.5-flash)
    except:
        return None
    return "models/gemini-1.5-flash" # Dự phòng

# --- HÀM 2: Gửi file lên Google để đọc (Xử lý Scan) ---
def process_file_scan(uploaded_file, api_key, model_name):
    try:
        genai.configure(api_key=api_key)
        # QUAN TRỌNG: Dùng đúng cái tên model vừa tìm được ở Hàm 1
        model = genai.GenerativeModel(model_name)
        
        # 1. Tạo file tạm
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        # 2. Upload lên Google
        myfile = genai.upload_file(tmp_path)
        
        # 3. Prompt lệnh
        prompt = """
        Trích xuất thông tin để đặt tên file PDF này.
        Cấu trúc: YYYYMMDD_LOAI_SoHieu_NoiDung_Signed.pdf
        
        Quy tắc:
        - YYYYMMDD: Năm tháng ngày (Ví dụ 20251231).
        - LOAI: QD, TTr, CV, TB, GP, HD, BB, BC...
        - SoHieu: Số hiệu (Ví dụ 125-UBND, thay / bằng -).
        - NoiDung: Tiếng Việt không dấu, nối bằng gạch dưới (_).
        
        Chỉ trả về duy nhất tên file kết quả.
        """
        
        # Chờ 2s cho file sẵn sàng
        time.sleep(2)
        
        # 4. Gọi AI
        result = model.generate_content([myfile, prompt])
        new_name = result.text.strip().replace("`", "")
        if not new_name.lower().endswith(".pdf"):
            new_name += ".pdf"
            
        # Dọn dẹp
        os.remove(tmp_path)
        return new_name, None
        
    except Exception as e:
        return None, str(e)

# --- Giao diện ---
if api_key:
    uploaded_files = st.file_uploader("Chọn file PDF (Scan/Ảnh đều được)", type=['pdf'], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 CHẠY LẦN CUỐI"):
        # Bước 1: Tìm model trước
        st.info("🤖 Đang tìm con AI phù hợp với Key của bạn...")
        active_model = get_best_model(api_key)
        
        if not active_model:
            st.error("❌ Key này không tìm thấy model nào. Kiểm tra lại Key.")
            st.stop()
            
        st.success(f"✅ Đã tìm thấy và dùng model: **{active_model}**")
        st.write("---")

        # Bước 2: Xử lý từng file
        for i, uploaded_file in enumerate(uploaded_files):
            with st.container():
                st.text(f"Đang gửi {uploaded_file.name} lên cho AI đọc...")
                
                # Gọi hàm xử lý với đúng model name vừa tìm được
                new_name, error_msg = process_file_scan(uploaded_file, api_key, active_model)
                
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
    st.warning("👉 Nhập Key đi huynh đài.")
