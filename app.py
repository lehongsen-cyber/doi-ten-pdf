import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader

# --- Cấu hình trang web ---
st.set_page_config(page_title="Đổi tên PDF - Tải Trực Tiếp", layout="centered")
st.title("📂 Đổi tên PDF & Tải File Luôn")
st.write("Xử lý xong file nào -> Hiện nút tải file đó.")

# --- Nhập API Key ---
with st.expander("🔑 Cài đặt API Key", expanded=True):
    api_key = st.text_input("Nhập Google API Key:", type="password")

# --- Hàm xử lý ---
def get_new_filename(text_content, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Nhiệm vụ: Đặt tên file ngắn gọn cho văn bản sau.
        Cấu trúc: YYYYMMDD_LOAI_SoHieu_NoiDung_Signed.pdf
        
        Quy tắc:
        - YYYYMMDD: Năm tháng ngày (Ví dụ 20251231).
        - LOAI: QD, TTr, CV, TB, GP, HD...
        - SoHieu: 125-UBND (Thay / bằng -).
        - NoiDung: Tiếng Việt không dấu, nối bằng gạch dưới (_).
        
        Văn bản:
        {text_content[:3000]} 

        Chỉ trả về 1 tên file duy nhất kết thúc bằng .pdf
        """
        
        response = model.generate_content(prompt)
        clean_name = response.text.strip().replace("`", "")
        if not clean_name.lower().endswith(".pdf"):
            clean_name += ".pdf"
        return clean_name, None
    except Exception as e:
        return None, str(e)

# --- Giao diện chính ---
if api_key:
    uploaded_files = st.file_uploader("Chọn file PDF", type=['pdf'], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 Xử lý ngay"):
        st.write("---")
        for i, uploaded_file in enumerate(uploaded_files):
            original_name = uploaded_file.name
            
            # Tạo container cho từng file để nhìn cho gọn
            with st.container():
                st.info(f"Đang đọc file: {original_name}...")
                
                try:
                    # Đọc PDF
                    reader = PdfReader(uploaded_file)
                    text = ""
                    if len(reader.pages) > 0:
                        text = reader.pages[0].extract_text()
                    
                    if not text:
                        text = "Văn bản scan không đọc được text"

                    # Gọi AI
                    new_name, error_msg = get_new_filename(text, api_key)
                    
                    if error_msg:
                        st.error(f"❌ Lỗi: {error_msg}")
                    else:
                        st.success(f"✅ Đã đổi tên thành: **{new_name}**")
                        
                        # --- NÚT TẢI PDF TRỰC TIẾP ---
                        # Đưa con trỏ file về đầu để đọc lại nội dung
                        uploaded_file.seek(0)
                        
                        st.download_button(
                            label=f"⬇️ BẤM ĐỂ TẢI: {new_name}",
                            data=uploaded_file,
                            file_name=new_name,
                            mime='application/pdf',
                            key=f"btn_{i}" # Key để không bị lỗi khi tải nhiều file
                        )
                    
                except Exception as e:
                    st.error(f"❌ Lỗi xử lý file {original_name}: {e}")
            
            st.write("---") # Đường gạch ngang phân cách các file

else:
    st.warning("👉 Nhập API Key ở trên để bắt đầu nhé!")
