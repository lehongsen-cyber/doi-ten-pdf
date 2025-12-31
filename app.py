import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import io

st.set_page_config(page_title="Đổi tên PDF - Auto Detect", layout="centered")
st.title("🛠️ Công cụ đổi tên PDF (Chế độ Tự Dò)")
st.write("Tự động tìm model AI phù hợp với API Key của bạn.")

with st.expander("🔑 Cài đặt API Key", expanded=True):
    api_key = st.text_input("Nhập Google API Key:", type="password")

# Hàm tự tìm model AI còn sống
def get_available_model(api_key):
    genai.configure(api_key=api_key)
    try:
        # Lấy danh sách tất cả model
        for m in genai.list_models():
            # Tìm model nào biết viết nội dung (generateContent) và là dòng Gemini
            if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name:
                return m.name # Trả về ngay cái tên đầu tiên tìm thấy
    except:
        return None
    return "gemini-1.5-flash" # Đường cùng thì thử cái này

def get_new_filename(text_content, api_key, model_name):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        prompt = f"""
        Nhiệm vụ: Đặt tên file ngắn gọn.
        Cấu trúc: YYYYMMDD_LOAI_SoHieu_NoiDung_Signed.pdf
        Quy tắc:
        - YYYYMMDD: Năm tháng ngày (Ví dụ 20251231).
        - LOAI: QD, TTr, CV, TB, GP, HD...
        - SoHieu: 125-UBND (Thay / bằng -).
        - NoiDung: Tiếng Việt không dấu, nối bằng gạch dưới (_).
        Văn bản: {text_content[:3000]} 
        Chỉ trả về 1 tên file duy nhất kết thúc bằng .pdf
        """
        response = model.generate_content(prompt)
        clean_name = response.text.strip().replace("`", "")
        if not clean_name.lower().endswith(".pdf"):
            clean_name += ".pdf"
        return clean_name, None
    except Exception as e:
        return None, str(e)

if api_key:
    uploaded_files = st.file_uploader("Chọn file PDF", type=['pdf'], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 Quét và Xử lý"):
        st.info("🤖 Đang dò tìm model AI phù hợp...")
        try:
            active_model = get_available_model(api_key)
            if active_model:
                st.success(f"Đã kết nối thành công với model: **{active_model}**")
            else:
                st.error("Không tìm thấy model nào hoạt động với Key này. Kiểm tra lại Key!")
                st.stop()
        except Exception as e:
            st.error(f"Lỗi kết nối Key: {e}")
            st.stop()

        st.write("---")
        for i, uploaded_file in enumerate(uploaded_files):
            with st.container():
                st.text(f"Đang đọc: {uploaded_file.name}...")
                try:
                    reader = PdfReader(uploaded_file)
                    text = ""
                    if len(reader.pages) > 0: text = reader.pages[0].extract_text()
                    if not text: text = "Không đọc được text"

                    # Dùng cái model vừa tìm được để chạy
                    new_name, error_msg = get_new_filename(text, api_key, active_model)
                    
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
                            key=f"btn_{i}"
                        )
                except Exception as e:
                    st.error(f"❌ Lỗi file: {e}")
            st.write("---")
