import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import io
import zipfile
import time

# --- Cấu hình trang web ---
st.set_page_config(page_title="Đổi tên PDF Chuẩn", layout="centered")
st.title("📂 Công cụ đổi tên PDF (Bản ổn định)")
st.write("Cấu trúc: YYYYMMDD_LOAI_SoHieu_NoiDung_Signed.pdf")

# --- Nhập API Key ---
with st.expander("🔑 Cài đặt API Key", expanded=True):
    api_key = st.text_input("Nhập Google API Key:", type="password")

# --- Hàm xử lý ---
def get_new_filename(text_content, api_key):
    try:
        genai.configure(api_key=api_key)
        # Chuyển sang model gemini-pro cho ổn định
        model = genai.GenerativeModel('gemini-1.5-flash') 
        
        prompt = f"""
        Nhiệm vụ: Đặt tên file cho văn bản dưới đây theo quy tắc:
        YYYYMMDD_LOAI_SoHieu_NoiDung_Signed.pdf

        Quy tắc:
        - YYYYMMDD: Năm tháng ngày văn bản (Ví dụ 20251231).
        - LOAI: QD, TTr, CV, TB, GP, HD, BB, BC...
        - SoHieu: 125-UBND (Thay / bằng -).
        - NoiDung: Tiếng Việt không dấu, nối bằng gạch dưới (_).
        
        Văn bản:
        {text_content[:4000]}

        Chỉ trả về 1 dòng tên file duy nhất.
        """
        response = model.generate_content(prompt)
        clean_name = response.text.strip().replace("`", "")
        if not clean_name.lower().endswith(".pdf"):
            clean_name += ".pdf"
        return clean_name
    except Exception as e:
        # Nếu lỗi thì trả về None để xử lý sau
        return None

# --- Giao diện chính ---
if api_key:
    uploaded_files = st.file_uploader("Chọn file PDF", type=['pdf'], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 Đổi tên ngay"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, uploaded_file in enumerate(uploaded_files):
                original_name = uploaded_file.name
                status_text.text(f"Đang xử lý: {original_name}...")
                
                try:
                    # Đọc PDF
                    reader = PdfReader(uploaded_file)
                    text = ""
                    for p in range(min(2, len(reader.pages))):
                        text += reader.pages[p].extract_text()
                    
                    if not text:
                        text = "Văn bản scan không đọc được text"

                    # Gọi AI
                    new_name = get_new_filename(text, api_key)
                    
                    # Nếu AI lỗi hoặc không trả về tên, dùng lại tên cũ thêm chữ _CheckLai
                    if new_name is None or "Loi_AI" in new_name:
                        new_name = f"ERROR_{original_name}"
                        results.append(f"⚠️ {original_name} -> **Lỗi kết nối AI (Giữ file gốc)**")
                    else:
                        results.append(f"✅ {original_name} -> **{new_name}**")
                    
                    # Quan trọng: Ghi nội dung file gốc vào tên mới
                    uploaded_file.seek(0)
                    zf.writestr(new_name, uploaded_file.read())
                    
                except Exception as e:
                    results.append(f"❌ {original_name}: Lỗi file - {e}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))

        status_text.text("Xử lý xong!")
        st.success("Hoàn thành!")
        
        for res in results:
            st.markdown(res)

        zip_buffer.seek(0)
        st.download_button(
            label="⬇️ Tải file PDF đã đổi tên (ZIP)",
            data=zip_buffer,
            file_name="File_PDF_Da_Doi_Ten.zip",
            mime="application/zip"
        )
