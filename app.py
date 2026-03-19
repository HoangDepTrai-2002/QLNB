import streamlit as st
from streamlit_option_menu import option_menu
from supabase import create_client, Client
import pandas as pd
from streamlit_calendar import calendar

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ thống Quản trị Nội bộ", layout="wide")

# --- 2. KẾT NỐI SUPABASE (Dán trực tiếp để bỏ qua lỗi Secrets) ---
url = "https://hbjlexconqjstongvxef.supabase.co"
key = "sb_publishable_nK8ZcjV3qb3M9HBm93hUNQ_03TKqBNf"
try:
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Lỗi kết nối Supabase: {e}")

# --- [MỚI] HỆ THỐNG ĐĂNG NHẬP (Giữ bảo mật cho bạn) ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 ĐĂNG NHẬP HỆ THỐNG")
    pw = st.text_input("Mật khẩu quản trị", type="password")
    if st.button("Truy cập"):
        if pw == "admin123":
            st.session_state.auth = True
            st.rerun()
        else: st.error("Sai mật khẩu!")
    st.stop()

# --- 3. THANH MENU BÊN TRÁI (Giữ nguyên cấu hình gốc) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
    st.title("Phần mềm Quản lý")
    selected = option_menu(
        menu_title="Danh mục chính",
        options=["Tổng quan", "Quản lý Nhân sự", "Lịch công tác"],
        icons=["house", "people", "calendar-event"],
        menu_icon="cast",
        default_index=0,
    )
    if st.button("🚪 Đăng xuất"):
        st.session_state.auth = False
        st.rerun()

# --- 4. XỬ LÝ CHI TIẾT TỪNG TRANG ---

# --- TRANG 1: TỔNG QUAN ---
if selected == "Tổng quan":
    st.header("📊 Báo cáo nhanh hệ thống")
    col1, col2, col3 = st.columns(3)
    try:
        res_nv = supabase.table("employees").select("id", count="exact").execute()
        res_lc = supabase.table("work_schedule").select("id", count="exact").execute()
        col1.metric("Tổng nhân viên", f"{res_nv.count if res_nv.count else 0} người")
        col2.metric("Lịch công tác", f"{res_lc.count if res_lc.count else 0} sự kiện")
        col3.metric("Trạng thái", "Trực tuyến", "100%")
        st.divider()
        # Khớp cột 'chu_vu' (viết thường) như trong hình image_5668d8.png
        res_all = supabase.table("employees").select("chu_vu").execute()
        if res_all.data:
            st.subheader("📈 Cơ cấu chức vụ nhân sự")
            df_chart = pd.DataFrame(res_all.data)
            st.bar_chart(df_chart['chu_vu'].value_counts())
    except Exception:
        st.info("💡 Mẹo: Hãy nhập dữ liệu ở các mục khác để biểu đồ hiện lên nhé!")

# --- TRANG 2: QUẢN LÝ NHÂN SỰ (Khớp 100% cột Database & Thêm tải ảnh) ---
elif selected == "Quản lý Nhân sự":
    st.header("👥 Quản lý lý lịch nhân viên")
    tab1, tab2 = st.tabs(["➕ Thêm mới", "📑 Danh sách"])
    
    with tab1:
        with st.form("add_nv", clear_on_submit=True):
            c1, c2 = st.columns(2)
            ten = c1.text_input("Họ và tên")
            ms = c2.text_input("Mã nhân viên")
            cv = st.selectbox("Chức vụ", ["Nhân viên", "Trưởng phòng", "Kế toán", "Kỹ thuật", "Quản lý"])
            # Thêm input tải ảnh nhân viên
            f_nv = st.file_uploader("Tải ảnh thẻ", type=['jpg','png'])
            
            if st.form_submit_button("Lưu vào hệ thống"):
                if ten and ms:
                    link_nv = ""
                    if f_nv:
                        try:
                            path_nv = f"nv_{ms}.png"
                            # Tải lên bucket 'images' (Bạn phải tạo bucket này trên Supabase)
                            supabase.storage.from_("images").upload(path_nv, f_nv.getvalue(), {"upsert": "true"})
                            link_nv = supabase.storage.from_("images").get_public_url(path_nv)
                        except: st.warning("Không tải được ảnh, sẽ lưu dữ liệu chữ.")
                    
                    # LƯU VÀO DATABASE (Khớp tên cột chuẩn: Ho_Ten, ma_vn, chu_vu, gh_chu)
                    data = {"Ho_Ten": ten, "ma_vn": ms, "chu_vu": cv, "gh_chu": link_nv}
                    try:
                        supabase.table("employees").insert(data).execute()
                        st.success(f"Đã thêm thành công nhân viên {ten}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi Database: {e}. Hãy đảm bảo đã tắt RLS cho bảng employees!")

    with tab2:
        res = supabase.table("employees").select("*").execute()
        if res.data:
            for item in res.data:
                with st.expander(f"👤 {item['Ho_Ten']} - {item['ma_vn']}"):
                    c_img, c_txt = st.columns([1, 4])
                    if item.get('gh_chu'): c_img.image(item['gh_chu'], width=100)
                    c_txt.write(f"**Chức vụ:** {item['chu_vu']}")
        else: st.info("Chưa có dữ liệu nhân viên.")

# --- TRANG 3: LỊCH CÔNG TÁC ---
elif selected == "Lịch công tác":
    st.header("📅 Hệ thống Lịch công tác")
    col_form, col_cal = st.columns([1, 2])
    with col_form:
        with st.form("work_form", clear_on_submit=True):
            content = st.text_input("Nội dung công việc")
            staff = st.text_input("Người thực hiện")
            date_val = st.date_input("Chọn ngày")
            if st.form_submit_button("Xác nhận đăng lịch"):
                if content and staff:
                    new_event = {"title": f"{staff}: {content}", "start": str(date_val), "end": str(date_val)}
                    supabase.table("work_schedule").insert(new_event).execute()
                    st.success("Đã cập nhật tờ lịch!")
                    st.rerun()
    with col_cal:
        try:
            res_cal = supabase.table("work_schedule").select("*").execute()
            calendar(events=res_cal.data if res_cal.data else [])
        except Exception:
            st.error("⚠️ Hãy đảm bảo đã tạo bảng 'work_schedule' và tắt RLS!")

