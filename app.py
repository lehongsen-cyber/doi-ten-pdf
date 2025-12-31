import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

# --- Cấu hình ---
st.set_page_config(page_title="Đổi tên PDF (Đã Fix File Lớn)", layout="centered")
st.title("🔥 Đổi tên PDF (Xử lý file nặng)")
st.write("Phiên bản thông minh: Tự động chờ file 50MB+ load xong mới chạy.")

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

# --- HÀM 2: Xử lý file (Có vòng lặp chờ) ---
def process_file_scan(uploaded_file, api_key, model_name):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # 1. Tạo file tạm
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        # 2. Upload lên Google
        myfile = genai.upload_file(tmp_path)
        
        # --- ĐOẠN MỚI: VÒNG LẶP CHỜ FILE LOAD XONG ---
        # File 58MB cần khoảng 10-20 giây để Google xử lý (state=PROCESSING)
        # Ta phải chờ nó chuyển sang state=ACTIVE thì mới dùng được.
        print(f"Dang cho xu ly file: {myfile.name}")
        
        while myfile.state.name == "PROCESSING":
            time.sleep(5) # Ngủ 5 giây rồi check lại
            myfile = genai.get_file(myfile.name) # Cập nhật trạng thái mới
            
        if myfile.state.name == "FAILED":
            raise ValueError("Google báo lỗi: Không thể đọc nội dung file này.")
            
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
    uploaded_files = st.file_uploader("Chọn file PDF", type=['pdf'], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 BẮT ĐẦU XỬ LÝ"):
        st.info("🤖 Đang kết nối AI...")
        active_model = get_best_model(api_key)
        
        if not active_model:
            st.error("❌ Key lỗi. Kiểm tra lại Key.")
            st.stop()
            
        st.success(f"✅ Đang dùng model: **{active_model}**")
        st.write("---")

        for i, uploaded_file in enumerate(uploaded_files):
            with st.container():
                st.text(f"⏳ Đang gửi file {uploaded_file.name} (File lớn sẽ lâu hơn xíu)...")
                
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
    st.warning("👉 Nhập Key để bắt đầu.")
