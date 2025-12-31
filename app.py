import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

# --- Cấu hình ---
st.set_page_config(page_title="Đổi tên PDF Scan", layout="centered")
st.title("👁️ Đổi tên PDF (Chuyên trị file Scan/Ảnh)")
st.write("Gửi thẳng file cho AI nhìn và đọc. Chấp cả file mờ, file chụp.")

# --- Nhập Key ---
with st.expander("🔑 Cài đặt API Key", expanded=True):
    api_key = st.text_input("Nhập Google API Key:", type="password")

# --- Hàm xử lý kiểu mới (Upload file lên Google) ---
def process_scanned_pdf(uploaded_file, api_key):
    try:
        genai.configure(api_key=api_key)
        # Dùng model 1.5 Flash vì nó hỗ trợ đọc file ảnh/pdf cực tốt
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 1. Lưu tạm file vào ổ cứng máy chủ để chuẩn bị upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        # 2. Upload file lên Google AI Studio
        myfile = genai.upload_file(tmp_path)
        
        # 3. Ra lệnh cho AI đọc file đó
        prompt = """
        Hãy nhìn vào tài liệu PDF này và trích xuất thông tin để đặt tên file mới.
        
        Cấu trúc bắt buộc: YYYYMMDD_LOAI_SoHieu_NoiDung_Signed.pdf
        
        Quy tắc:
        - YYYYMMDD: Ngày ban hành văn bản (Năm tháng ngày). Ví dụ 20251231.
        - LOAI: QD, TTr, CV, TB, GP, HD, BB, BC...
        - SoHieu: Số hiệu văn bản (Ví dụ 125-UBND). Thay dấu / bằng dấu -.
        - NoiDung: Tóm tắt nội dung chính bằng Tiếng Việt KHÔNG DẤU, nối bằng dấu gạch dưới (_).
        
        Yêu cầu: Chỉ trả về duy nhất 1 dòng là tên file mới. Không giải thích gì thêm.
        """
        
        # Chờ 2 giây để file được xử lý bên Google
        time.sleep(2)
        
        result = model.generate_content([myfile, prompt])
        new_name = result.text.strip().replace("`", "")
        if not new_name.lower().endswith(".pdf"):
            new_name += ".pdf"
            
        # 4. Dọn dẹp (Xóa file tạm)
        os.remove(tmp_path)
        return new_name, None
        
    except Exception as e:
        return None, str(e)

# --- Giao diện ---
if api_key:
    uploaded_files = st.file_uploader("Chọn file PDF (Scan cũng chơi tất)", type=['pdf'], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 Soi và Đổi tên"):
        st.write("---")
        for i, uploaded_file in enumerate(uploaded_files):
            with st.container():
                st.info(f"Đang gửi file {uploaded_file.name} lên Google để đọc...")
                
                # Gọi hàm xử lý kiểu mới
                new_name, error_msg = process_scanned_pdf(uploaded_file, api_key)
                
                if error_msg:
                    # Lỗi thì báo đỏ
                    st.error(f"❌ Lỗi: {error_msg}")
                else:
                    # Thành công
                    st.success(f"✅ Đọc xong: **{new_name}**")
                    
                    # Nút tải về
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
    st.warning("👉 Nhập Key đi rồi mình làm việc.")
