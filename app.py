import streamlit as st
import requests
import re
import time
from urllib.parse import quote
from playwright.sync_api import sync_playwright
import jdatetime

st.set_page_config(page_title="داشبورد مدیریت و پایش قیمت رقبا", layout="wide")

# ================= رمز عبور ادمین =================
ADMIN_PASSWORD = "Admin@1405"  # می‌توانید رمز عبور را اینجا تغییر دهید

# ================= سیستم احراز هویت (Login) =================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
            <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 25px; border-radius: 12px; color: white; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                <h3>🔐 ورود به داشبورد مدیریت قیمت</h3>
                <p style="font-size: 13px; opacity: 0.9;">لطفاً رمز عبور مدیریت را وارد کنید</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            password_input = st.text_input("رمز عبور", type="password")
            submit_login = st.form_submit_button("ورود به سیستم", use_container_width=True)
            
            if submit_login:
                if password_input == ADMIN_PASSWORD:
                    st.session_state["authenticated"] = True
                    st.success("ورود موفقیت‌آمیز بود! در حال انتقال...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("رمز عبور اشتباه است.")
    st.stop()

# تابع تبدیل اعداد انگلیسی به فارسی
def to_persian_num(text):
    if not text:
        return ""
    persian_nums = {'0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'}
    return ''.join(persian_nums.get(char, char) for char in str(text))

# تابع تبدیل تاریخ میلادی ووکامرس به تاریخ و ساعت کاملاً شمسی
def format_jalali_date(date_str):
    if not date_str:
        return "نامشخص"
    try:
        clean_date = date_str.replace('T', ' ')[:19]
        dt_gregorian = time.strptime(clean_date, "%Y-%m-%d %H:%M:%S")
        dt_jalali = jdatetime.datetime.fromgregorian(
            year=dt_gregorian.tm_year,
            month=dt_gregorian.tm_mon,
            day=dt_gregorian.tm_mday,
            hour=dt_gregorian.tm_hour,
            minute=dt_gregorian.tm_min
        )
        jalali_str = dt_jalali.strftime("%Y/%m/%d - %H:%M")
        return to_persian_num(jalali_str)
    except:
        return "نامشخص"

# استایل‌های حرفه‌ای جدول و داشبورد
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Vazirmatn', sans-serif;
        direction: rtl;
        text-align: right;
    }
    .main-header {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        color: white;
        padding: 24px;
        border-radius: 14px;
        margin-bottom: 25px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.15);
    }
    .row-card-comp {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border: 1px solid #bbf7d0;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        transition: all 0.2s ease;
    }
    .row-card-normal {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        transition: all 0.2s ease;
    }
    .price-badge {
        font-size: 14px;
        font-weight: 700;
        color: #0369a1;
        background: #e0f2fe;
        padding: 4px 8px;
        border-radius: 6px;
    }
    .comp-badge {
        font-size: 14px;
        font-weight: 700;
        color: #166534;
        background: #bbf7d0;
        padding: 4px 8px;
        border-radius: 6px;
    }
    .time-badge {
        font-size: 12px;
        color: #64748b;
        background: #f1f5f9;
        padding: 3px 6px;
        border-radius: 4px;
        display: inline-block;
        margin-top: 4px;
    }
    </style>
""", unsafe_allow_html=True)

WP_SITE = "https://sigmamed.ir"
WP_KEY = "ck_de0c5a8a465aed438c4a45ed8ff5a010d844f4e0"
WP_SECRET = "cs_aa3950c0ce558941fd741889b5006c69806d445a"

def get_precise_price(url, locator_str):
    try:
        if "digikala.com" in url:
            parts = url.split("?")
            base_url = parts[0]
            safe_url = quote(base_url, safe=':/%')
        else:
            safe_url = quote(url, safe=':/%')

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, channel="chrome")
            page = browser.new_page()
            try:
                response = page.goto(safe_url, timeout=30000)
                if not response or response.status != 200:
                    browser.close()
                    return None
            except:
                browser.close()
                return None
            
            page.wait_for_timeout(4000)
            raw_text = ""
            
            if locator_str and locator_str.strip():
                try:
                    target = locator_str.strip()
                    if target.startswith(("/", "(", "[")):
                        if target.endswith("/text()"): target = target[:-7]
                        raw_text = page.locator(f"xpath={target}").first.inner_text()
                    else:
                        raw_text = page.locator(target).first.inner_text()
                except: pass
            
            if not raw_text:
                for sel in [".price_style", ".dg-text-xl", ".price bdi", "ins bdi", ".amount"]:
                    try:
                        element = page.locator(sel).first
                        if element.count() > 0:
                            raw_text = element.inner_text()
                            if raw_text:
                                break
                    except: continue
            
            browser.close()
            
            if raw_text:
                nums = re.findall(r'\d+', raw_text.replace(',', ''))
                if nums:
                    price = float(''.join(nums))
                    if price > 10000:
                        return price
        return None
    except: return None

def update_meta_data(product_id, comp_price):
    try:
        ts = int(time.time())
        res_get = requests.get(f"{WP_SITE}/wp-json/wc/v3/products/{product_id}?_t={ts}", auth=(WP_KEY, WP_SECRET), timeout=10)
        if res_get.status_code != 200: return False
        product_data = res_get.json()
        meta_list = product_data.get('meta_data', [])
        updated = False
        for m in meta_list:
            if m['key'] == '_competitor_last_price':
                m['value'] = str(int(comp_price))
                updated = True
        if not updated:
            meta_list.append({'key': '_competitor_last_price', 'value': str(int(comp_price))})
        res = requests.put(f"{WP_SITE}/wp-json/wc/v3/products/{product_id}?_t={ts}", json={"meta_data": meta_list}, auth=(WP_KEY, WP_SECRET), timeout=10)
        return res.status_code == 200
    except: return False

# دکمه خروج در سایدبار
if st.sidebar.button("🚪 خروج از حساب کاربری"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")

st.markdown("""
    <div class="main-header">
        <h2 style="margin:0;">🛡️ داشبورد پیشرفته پایش و مدیریت هوشمند قیمت رقبا</h2>
        <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">مدیریت جامع محصولات، رصد هوشمند و به‌روزرسانی قیمت‌ها</p>
    </div>
""", unsafe_allow_html=True)

if st.button("🔄 بروزرسانی و دریافت مجدد اطلاعات از سرور"):
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=30)
def get_woo_data():
    try:
        ts = int(time.time())
        p_res = requests.get(f"{WP_SITE}/wp-json/wc/v3/products?per_page=100&_t={ts}", auth=(WP_KEY, WP_SECRET), timeout=15)
        c_res = requests.get(f"{WP_SITE}/wp-json/wc/v3/products/categories?per_page=100&_t={ts}", auth=(WP_KEY, WP_SECRET), timeout=15)
        products = p_res.json() if p_res.status_code == 200 else []
        categories = c_res.json() if c_res.status_code == 200 else []
        return products, categories
    except:
        return [], []

with st.spinner("در حال دریافت اطلاعات محصولات از ووکامرس..."):
    products, categories = get_woo_data()

if products:
    cat_dict = {'all': "📂 همه محصولات"}
    for c in categories:
        cat_dict[c['id']] = c['name']

    st.sidebar.markdown("### 🗂️ دسته‌بندی محصولات")
    selected_cat_name = st.sidebar.selectbox("انتخاب کنید:", list(cat_dict.values()), index=0)
    
    selected_cat_id = 'all'
    for k, v in cat_dict.items():
        if v == selected_cat_name:
            selected_cat_id = k
            break

    filtered_products = []
    for p in products:
        if selected_cat_id == 'all':
            filtered_products.append(p)
        else:
            p_cats = [cat['id'] for cat in p.get('categories', [])]
            if selected_cat_id in p_cats:
                filtered_products.append(p)

    st.markdown(f"### 📋 لیست محصولات دسته‌بندی: {selected_cat_name} (مجموع: {to_persian_num(len(filtered_products))} محصول)")
    st.markdown("---")

    if filtered_products:
        for p in filtered_products:
            meta = {m['key']: m['value'] for m in p.get('meta_data', [])}
            url = meta.get('_competitor_url')
            locator_str = meta.get('_competitor_css_class', '')
            has_competitor = bool(url and url.strip())
            
            price_key = f"current_price_{p['id']}"
            if price_key not in st.session_state:
                st.session_state[price_key] = p.get('price', '0')
            current_price = st.session_state[price_key]
            
            comp_key = f"comp_price_{p['id']}"
            if comp_key not in st.session_state:
                st.session_state[comp_key]  = meta.get('_competitor_last_price', 'بررسی نشده')
            last_comp_price = st.session_state[comp_key]

            date_mod = p.get('date_modified', '')
            formatted_date = format_jalali_date(date_mod)

            row_style = "row-card-comp" if has_competitor else "row-card-normal"

            with st.container():
                st.markdown(f'<div class="{row_style}">', unsafe_allow_html=True)
                col1, col2, col3, col4 = st.columns([2.6, 1.2, 1.3, 1.9])
                
                with col1:
                    status_icon = "🟢" if has_competitor else "⚪"
                    st.markdown(f"**{status_icon} {p['name']}**")
                    if has_competitor:
                        st.markdown(f"🔗 [مشاهده لینک رقیب]({url})")
                    else:
                        st.caption("لینک رقیب تعریف نشده است")
                
                with col2:
                    st.caption("قیمت فعلی سایت")
                    st.markdown(f"<span class='price-badge'>{to_persian_num(f'{int(float(current_price or 0)):,}')} تومان</span>", unsafe_allow_html=True)
                    st.markdown(f"<span class='time-badge'>⏰ ویرایش: {formatted_date}</span>", unsafe_allow_html=True)
                
                with col3:
                    st.caption("آخرین قیمت رقیب")
                    if has_competitor:
                        disp_comp = f"{to_persian_num(f'{int(float(last_comp_price)):,}')} تومان" if str(last_comp_price).isdigit() else "پایش نشده"
                        st.markdown(f"<span class='comp-badge'>{disp_comp}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='color: #94a3b8; font-size: 13px;'>فاقد رقیب</span>", unsafe_allow_html=True)
                
                with col4:
                    st.caption("عملیات مدیریتی")
                    if has_competitor:
                        sub_col1, sub_col2 = st.columns(2)
                        with sub_col1:
                            if st.button("🔍 پایش", key=f"check_{p['id']}"):
                                with st.spinner("در حال پایش..."):
                                    comp_price = get_precise_price(url, locator_str)
                                    if comp_price:
                                        update_meta_data(p['id'], comp_price)
                                        st.session_state[comp_key] = str(int(comp_price))
                                        st.toast(f"✅ پایش شد: {to_persian_num(f'{int(comp_price):,}')} تومان", icon="🎯")
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error("پیدا نشد!")
                        with sub_col2:
                            if str(last_comp_price).isdigit():
                                if st.button("🚀 اعمال", key=f"apply_{p['id']}"):
                                    with st.spinner("در حال اعمال..."):
                                        c_price = float(last_comp_price)
                                        percent = float(meta.get('_competitor_adj_percent', 0) or 0)
                                        
                                        new_price = c_price + (c_price * (percent / 100))
                                        new_price = round(new_price / 1000) * 1000
                                        
                                        min_p = float(meta.get('_competitor_min_price', 0) or 0)
                                        if min_p > 0 and new_price < min_p: new_price = min_p
                                        max_p = float(meta.get('_competitor_max_price', 0) or 0)
                                        if max_p > 0 and new_price > max_p: new_price = max_p
                                        
                                        ts = int(time.time())
                                        update_data = {"regular_price": str(int(new_price)), "price": str(int(new_price))}
                                        update_res = requests.put(f"{WP_SITE}/wp-json/wc/v3/products/{p['id']}?_t={ts}", json=update_data, auth=(WP_KEY, WP_SECRET))
                                        
                                        if update_res.status_code == 200:
                                            st.session_state[price_key] = str(int(new_price))
                                            st.toast(f"✅ به {to_persian_num(f'{int(new_price):,}')} تومان آپدیت شد!", icon="🚀")
                                            st.cache_data.clear()
                                            st.rerun()
                                        else:
                                            st.error("خطا در ثبت!")
                            else:
                                st.button("🚀 اعمال", key=f"apply_disabled_{p['id']}", disabled=True)
                    else:
                        st.info("غیرقابل پایش")
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("محصولی در این دسته‌بندی یافت نشد.")
else:
    st.warning("محصولی از ووکامرس دریافت نشد یا اتصال با خطا مواجه شد.")