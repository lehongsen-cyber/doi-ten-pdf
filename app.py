import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import io
import zipfile

# --- Cấu hình trang web ---
st.set_page_config(page_title="Đổi tên PDF Chuẩn Quy Tắc", layout="centered")

st.title("📂 Công cụ đổi tên PDF theo Quy chuẩn")
st.write("Cấu trúc: YYYYMMDD_LOAI_SoHieu_NoiDung_Signed.pdf")

# --- Nhập API Key ---
with st.expander("🔑 Cài đặt API Key (Bắt buộc)", expanded=True):
    api_key = st.text_input("Dán Google API Key của bạn vào đây:", type="password")
    st.markdown("Chưa có Key? [Lấy miễn phí tại đây](https://aistudio.google.com/app/apikey)")

# --- Hàm xử lý ---
def get_new_filename(text_content, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Cập nhật Prompt theo file quy tắc mới
        prompt = f"""
        Bạn là trợ lý văn thư chuyên nghiệp. Hãy đặt tên file dựa trên nội dung văn bản theo quy tắc đặt tên file chuẩn (Naming Convention) sau đây:

        1. CẤU TRÚC: YYYYMMDD_LOAI_SoHieu_NoiDung_TrangThai.pdf

        2. QUY TẮC CHI TIẾT:
           - YYYYMMDD: Năm-Tháng-Ngày ban hành văn bản (Viết liền, không dấu gạch). Ví dụ: 20251231.
           - LOAI: Xác định và viết tắt loại văn bản:
             + QD (Quyết định), TTr (Tờ trình), CV (Công văn), TB (Thông báo)
             + GP (Giấy phép), HD (Hợp đồng), BB (Biên bản), BC (Báo cáo)
           - SoHieu: Số hiệu văn bản. Thay dấu gạch chéo (/) bằng dấu gạch ngang (-). Ví dụ: 125/UBND -> 125-UBND.
           - NoiDung: Tóm tắt ngắn gọn nội dung chính bằng TIẾNG VIỆT KHÔNG DẤU, nối bằng dấu gạch dưới (_).
           - TrangThai: Mặc định luôn để là "Signed" (vì đây là file scan).

        3. VÍ DỤ MẪU:
           Input: Một quyết định giao đất số 125/UBND ngày 15/08/2025.
           Output: 20250815_QD_125-UBND_Giao_dat_Dot1_Signed.pdf

        YÊU CẦU ĐẶC BIỆT: 
        - Chỉ trả về duy nhất tên file kết quả. Không giải thích gì thêm.
        - Đảm bảo đúng thứ tự và dùng dấu gạch dưới (_) để nối các phần.
        
        Nội dung văn bản cần đặt tên:
        {text_content[:5000]}
        """
        
        response = model.generate_content(prompt)
        # Làm sạch chuỗi kết quả (bỏ khoảng trắng thừa, bỏ dấu ngoặc nếu AI lỡ thêm vào)
        clean_name = response.text.strip().replace("`", "").replace(".pdf", "")
        return clean_name + ".pdf"
        
    except Exception as e:
        return f"Loi_AI_{str(e)[:10]}.pdf"

# --- Giao diện chính ---
if api_key:
    uploaded_files = st.file_uploader("Chọn file PDF (Scan/Văn bản)", type=['pdf'], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 Thực hiện đổi tên"):
        progress_bar = st.progress(0)
        results = []
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, uploaded_file in enumerate(uploaded_files):
                try:
                    reader = PdfReader(uploaded_file)
                    text = ""
                    # Cố gắng đọc 2 trang đầu để lấy đủ thông tin ngày tháng/số hiệu
                    num_pages = len(reader.pages)
                    read_pages = min(2, num_pages)
                    for p in range(read_pages):
                        text += reader.pages[p].extract_text()
                    
                    if not text:
                        text = "Không đọc được text (File ảnh scan chưa OCR)"

                    new_name = get_new_filename(text, api_key)
                    
                    # Kiểm tra lại đuôi pdf lần nữa cho chắc
                    if not new_name.lower().endswith(".pdf"):
                        new_name += ".pdf"
                        
                    results.append(f"✅ {uploaded_file.name} \n   -> **{new_name}**")
                    
                    uploaded_file.seek(0)
                    zf.writestr(new_name, uploaded_file.read())
                    
                except Exception as e:
                    results.append(f"❌ {uploaded_file.name}: Lỗi - {e}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))

        st.success("Xử lý hoàn tất!")
        for res in results:
            st.markdown(res)
            st.markdown("---")

        zip_buffer.seek(0)
        st.download_button(
            label="⬇️ Tải về tất cả (ZIP)",
            data=zip_buffer,
            file_name="Ho_so_da_chuan_hoa.zip",
            mime="application/zip"
        )
else:
    st.info("👋 Xin chào! Vui lòng nhập Google API Key để bắt đầu.")
