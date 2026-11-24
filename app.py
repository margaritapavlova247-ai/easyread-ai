import streamlit as st
import json, os, hashlib, hmac
import urllib.request, urllib.parse
from datetime import datetime
from PIL import Image, ImageEnhance
from groq import Groq

GROQ_KEY = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
SB_URL = st.secrets.get("SUPABASE_URL", "").rstrip("/") if hasattr(st, "secrets") else ""
SB_KEY = st.secrets.get("SUPABASE_KEY", "") if hasattr(st, "secrets") else ""

client = Groq(api_key=GROQ_KEY)

st.set_page_config(page_title="StudyBox", page_icon="📖", layout="centered")

def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

def make_auth_token(username, password_hash):
    return hmac.new(SB_KEY.encode(), f"{username}:{password_hash}".encode(), hashlib.sha256).hexdigest()[:24]

def sb_request(method, endpoint, data=None):
    url = f"{SB_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else []

def get_user_record(username):
    safe_u = urllib.parse.quote(username)
    rows = sb_request("GET", f"studybox_users?username=eq.{safe_u}&select=*")
    return rows.pop(0) if rows else None

def register_user_db(username, password):
    if get_user_record(username):
        return False
    sb_request("POST", "studybox_users", {
        "username": username,
        "password_hash": hash_pass(password),
        "notebooks": {"Общая тетрадь": []}
    })
    return True

def get_user_notebooks(username):
    rec = get_user_record(username)
    if rec and isinstance(rec.get("notebooks"), dict):
        return rec.get("notebooks")
    return {"Общая тетрадь": []}

def save_user_notebooks(username, notebooks):
    safe_u = urllib.parse.quote(username)
    sb_request("PATCH", f"studybox_users?username=eq.{safe_u}", {"notebooks": notebooks})

def read_uploaded_photo(uploaded_file):
    import pytesseract

    img = Image.open(uploaded_file).convert("RGB")
    w, h = img.size
    if w < 1600:
        scale = 1600 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.0)

    raw_text = pytesseract.image_to_string(img, lang="rus+ron+eng").strip()
    if not raw_text:
        raise Exception("На фото не удалось найти печатный текст. Попробуй сфотографировать страницу учебника ближе и при хорошем свете.")

    clean_resp = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=(
            {"role": "system", "content": "Ты корректор текста. Тебе дают текст, распознанный с фотографии страницы учебника (на русском, румынском или английском). Исправь случайные опечатки распознавания, аккуратно оформи формулы и собери текст в ровные абзацы, сохраняя весь смысл слово в слово. Не добавляй своих комментариев — верни ТОЛЬКО исправленный текст."},
            {"role": "user", "content": raw_text}
        )
    )
    return clean_resp.choices.pop(0).message.content.strip()

defaults = (
    ("current_user", None),
    ("source_text", ""),
    ("adapted_text", ""),
    ("quiz_data", None),
    ("show_quiz", False),
    ("grade_result", None),
    ("active_notebook", None),
    ("show_new_nb_form", False)
)
for key, val in defaults:
    if key not in st.session_state:
        st.session_state[key] = val

# Безопасное восстановление сессии только на этом устройстве через подписанный токен в браузере
if not st.session_state.current_user:
    q_user = st.query_params.get("u", "")
    q_tok = st.query_params.get("t", "")
    if q_user and q_tok:
        try:
            rec = get_user_record(q_user)
            if rec and make_auth_token(q_user, rec.get("password_hash", "")) == q_tok:
                st.session_state.current_user = q_user
        except Exception:
            pass

st.markdown("""
    <style>
    @import url('https://googleapis.com');
    html, body, p, div, label, input, textarea, select, button { font-family: 'Nunito', sans-serif !important; }
    .auth-header {
        background: linear-gradient(135deg, #5B4BC4 0%, #8E7FF5 100%);
        padding: 40px 32px; border-radius: 26px; color: white; text-align: center;
        margin-bottom: 30px; box-shadow: 0 16px 40px rgba(91, 75, 196, 0.22);
    }
    .auth-header h1 { font-size: 38px !important; font-weight: 900 !important; margin: 0 !important; }
    .auth-header p { font-size: 20px !important; margin-top: 12px !important; opacity: 0.95; }
    </style>
""", unsafe_allow_html=True)

if not st.session_state.current_user:
    st.markdown('<div class="auth-header" translate="no"><h1>StudyBox</h1><p>Личный кабинет ученика — твои тетради сохраняются навсегда</p></div>', unsafe_allow_html=True)
    tab_login, tab_reg = st.tabs(("Вход в аккаунт", "Регистрация"))

    with tab_login:
        with st.form("login_form"):
            nick = st.text_input("Никнейм:")
            pwd = st.text_input("Пароль:", type="password")
            rem = st.checkbox("Запомнить меня на этом устройстве", value=True)
            if st.form_submit_button("Войти в кабинет"):
                clean_nick = nick.strip()
                try:
                    rec = get_user_record(clean_nick)
                    if rec and rec.get("password_hash") == hash_pass(pwd):
                        st.session_state.current_user = clean_nick
                        if rem:
                            st.query_params["u"] = clean_nick
                            st.query_params["t"] = make_auth_token(clean_nick, rec.get("password_hash"))
                        st.rerun()
                    else:
                        st.error("Неверный никнейм или пароль.")
                except Exception as e:
                    st.error(f"Ошибка подключения к базе: {e}")

    with tab_reg:
        with st.form("reg_form"):
            r_nick = st.text_input("Придумай никнейм:")
            r_pwd = st.text_input("Придумай пароль (от 4 символов):", type="password")
            r_pwd2 = st.text_input("Повтори пароль:", type="password")
            r_rem = st.checkbox("Запомнить меня на этом устройстве", value=True)
            if st.form_submit_button("Создать аккаунт"):
                clean_r = r_nick.strip()
                if not clean_r or len(r_pwd) < 4:
                    st.warning("Введи никнейм и пароль (минимум 4 символа).")
                elif r_pwd != r_pwd2:
                    st.error("Пароли не совпадают.")
                else:
                    try:
                        if register_user_db(clean_r, r_pwd):
                            st.session_state.current_user = clean_r
                            if r_rem:
                                st.query_params["u"] = clean_r
                                st.query_params["t"] = make_auth_token(clean_r, hash_pass(r_pwd))
                            st.rerun()
                        else:
                            st.error("Этот никнейм уже занят.")
                    except Exception as e:
                        st.error(f"Ошибка регистрации: {e}")
    st.stop()
notebooks = get_user_notebooks(st.session_state.current_user)

with st.sidebar:
    st.markdown(f"<div style='font-size:22px; font-weight:800; margin-bottom:8px;'>Профиль: {st.session_state.current_user}</div>", unsafe_allow_html=True)
    if st.button("Выйти из аккаунта", key="logout_btn"):
        st.session_state.current_user = None
        st.session_state.active_notebook = None
        st.session_state.source_text = ""
        st.session_state.adapted_text = ""
        st.query_params.clear()
        st.rerun()

    st.markdown("<hr style='margin:16px 0;'>", unsafe_allow_html=True)

    if st.button("Новый конспект", key="home_btn"):
        st.session_state.active_notebook = None
        st.rerun()

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    col_title, col_plus = st.columns((4, 1))
    with col_title:
        st.markdown("<div style='font-size:20px; font-weight:800; padding-top:4px;'>Мои тетради</div>", unsafe_allow_html=True)
    with col_plus:
        if st.button("+", key="add_nb_btn", help="Создать новую тетрадь"):
            st.session_state.show_new_nb_form = not st.session_state.show_new_nb_form

    if st.session_state.show_new_nb_form:
        with st.form("new_nb_form"):
            new_nb_name = st.text_input("Название тетради:", placeholder="Например: География")
            if st.form_submit_button("Создать"):
                clean_name = new_nb_name.strip()
                if clean_name and clean_name not in notebooks:
                    notebooks.update({clean_name: list()})
                    save_user_notebooks(st.session_state.current_user, notebooks)
                    st.session_state.show_new_nb_form = False
                    st.session_state.active_notebook = clean_name
                    st.rerun()
                elif clean_name in notebooks:
                    st.warning("Такая тетрадь уже есть.")

    for nb_name in tuple(notebooks.keys()):
        notes_count = len(notebooks.get(nb_name, ()))
        label_text = f"{nb_name}  ({notes_count})" if notes_count > 0 else nb_name
        if st.button(label_text, key=f"nb_btn_{nb_name}"):
            st.session_state.active_notebook = nb_name
            st.rerun()

    st.markdown("<hr style='margin:20px 0;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:20px; font-weight:800; margin-bottom:8px;'>Оформление страницы</div>", unsafe_allow_html=True)
    theme = st.selectbox("Оттенок фона:", ("Мягкий кремовый", "Нежно-мятный", "Спокойный голубой"))
    font_size = st.slider("Размер текста:", min_value=18, max_value=28, value=22)

bg_color = "#F8F4EC" if "кремовый" in theme else ("#EDF6F1" if "мятный" in theme else "#ECF3FA")
accent_color = "#5B4BC4" if "кремовый" in theme else ("#0D8A72" if "мятный" in theme else "#2563EB")
accent_light = "#8E7FF5" if "кремовый" in theme else ("#34D399" if "мятный" in theme else "#60A5FA")

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: #1A1D26; }}
    .block-container {{ max-width: 840px !important; padding-top: 2.5rem !important; padding-bottom: 4rem !important; }}
    p, label, .stMarkdown p, .stRadio label p, .stSelectbox label p, .stSlider label p, .stTextArea label p, .stTextInput label p {{
        font-size: 20px !important; line-height: 1.65 !important;
    }}
    div[role="radiogroup"] label {{
        background-color: #FFFFFF; padding: 14px 18px !important; border-radius: 14px !important;
        border: 1px solid rgba(0,0,0,0.06) !important; margin-bottom: 10px !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.02); transition: 0.2s;
    }}
    div[role="radiogroup"] label:hover {{ border-color: {accent_color} !important; transform: translateX(4px); }}
    textarea, input[type="text"] {{ font-size: 19px !important; border-radius: 14px !important; padding: 14px !important; }}
    .hero-box {{
        background: linear-gradient(135deg, {accent_color} 0%, {accent_light} 100%);
        padding: 38px 34px; border-radius: 26px; color: white; margin-bottom: 32px;
        box-shadow: 0 18px 40px rgba(0,0,0,0.1);
    }}
    .hero-badge {{
        display: inline-block; background: rgba(255,255,255,0.2); padding: 6px 14px;
        border-radius: 20px; font-size: 14px !important; font-weight: 800;
        letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 12px;
    }}
    .hero-title {{ font-size: 40px !important; font-weight: 900 !important; margin: 0 !important; }}
    .hero-sub {{ font-size: 20px !important; opacity: 0.95; margin-top: 12px !important; }}
    .section-title {{ font-size: 25px !important; font-weight: 800 !important; color: #1A1D26; margin-top: 24px !important; margin-bottom: 12px !important; }}
    div.stVerticalBlockBorderWrapper {{
        background-color: #FFFFFF !important; border-radius: 22px !important; border: none !important;
        border-left: 7px solid {accent_color} !important; padding: 22px 26px !important;
        box-shadow: 0 12px 32px rgba(0,0,0,0.06) !important; margin: 18px 0 !important;
    }}
    div.stVerticalBlockBorderWrapper p {{ font-size: {font_size}px !important; line-height: 1.75 !important; margin-bottom: 14px !important; }}
    .a4-paper {{
        background-color: #FFFFFF; padding: 32px; border-radius: 12px; border: 1px solid #E2E8F0;
        box-shadow: 0 14px 36px rgba(0,0,0,0.08); margin: 28px 0 18px 0;
        border-top: 9px solid {accent_color}; text-align: center;
    }}
    .grade-box {{
        background-color: #FFF5F5; border: 3px solid #E02424; border-radius: 24px;
        padding: 30px; text-align: center; margin-top: 24px; box-shadow: 0 12px 30px rgba(224, 36, 36, 0.12);
    }}
    .grade-number {{ font-size: 80px !important; font-weight: 900 !important; color: #E02424; line-height: 1.1 !important; }}
    @keyframes shimmer {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}
    section.main div.stButton > button {{
        background: linear-gradient(270deg, {accent_color}, {accent_light}, {accent_color});
        background-size: 200% 200%; animation: shimmer 5s ease infinite; color: white !important;
        font-size: 20px !important; font-weight: 800 !important; padding: 14px 24px !important;
        border-radius: 16px !important; border: none !important; width: 100%; margin-top: 8px !important;
    }}
    section[data-testid="stSidebar"] div.stButton > button {{
        background: transparent !important; animation: none !important; color: #1A1D26 !important;
        font-size: 18px !important; font-weight: 600 !important; padding: 8px 12px !important;
        border-radius: 10px !important; border: none !important; box-shadow: none !important;
        text-align: left !important; justify-content: flex-start !important;
        margin-top: 2px !important; margin-bottom: 2px !important; width: 100%;
    }}
    section[data-testid="stSidebar"] div.stButton > button:hover {{ background-color: rgba(0, 0, 0, 0.06) !important; }}
    </style>
""", unsafe_allow_html=True)
if st.session_state.active_notebook:
    nb_title = st.session_state.active_notebook
    st.markdown(f"""
        <div class="hero-box" translate="no">
            <div class="hero-badge">Личная тетрадь</div>
            <div class="hero-title">{nb_title}</div>
            <div class="hero-sub">Здесь хранятся все твои сохранённые конспекты по этому предмету. Нажми на любую тему, чтобы открыть её.</div>
        </div>
    """, unsafe_allow_html=True)

    saved_notes = notebooks.get(nb_title, ())
    if not saved_notes:
        st.info("В этой тетради пока пусто. Перейди на «Новый конспект», создай материал и нажми «Сохранить в тетрадь».")
    else:
        for idx, note in enumerate(saved_notes):
            with st.expander(f"{note.get('topic', 'Без названия')} — {note.get('date', '')}"):
                st.markdown(note.get("content", ""))
                if st.button("Удалить этот конспект", key=f"del_{nb_title}_{idx}"):
                    updated_list = list(saved_notes)
                    updated_list.pop(idx)
                    notebooks.update({nb_title: updated_list})
                    save_user_notebooks(st.session_state.current_user, notebooks)
                    st.rerun()
    st.stop()

st.markdown(f"""
    <div class="hero-box" translate="no">
        <div class="hero-badge">Умный помощник для учёбы</div>
        <div class="hero-title">StudyBox</div>
        <div class="hero-sub">Привет, <b>{st.session_state.current_user}</b>! Вставь текст или загрузи фото страницы учебника — я переведу её в понятный конспект и проверю знания тестом.</div>
    </div>
""", unsafe_allow_html=True)

col_sec1, col_clr = st.columns((3, 1))
with col_sec1:
    st.markdown('<div class="section-title">1. Исходный текст из учебника</div>', unsafe_allow_html=True)
with col_clr:
    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
    if st.button("Очистить поле", key="clear_text_btn"):
        st.session_state.source_text = ""
        st.session_state.adapted_text = ""
        st.session_state.show_quiz = False
        st.session_state.grade_result = None
        st.rerun()

tab_txt, tab_img = st.tabs(("Вставить текст", "Загрузить или сфоткать страницу"))

with tab_img:
    photo_file = st.file_uploader("Выбери фото страницы учебника или сделай снимок на телефоне:", type=("jpg", "jpeg", "png"))
    if photo_file is not None:
        st.image(photo_file, caption="Загруженная страница", use_container_width=True)
        if st.button("Распознать текст с фото", key="ocr_upload_btn"):
            with st.spinner("Улучшаю чёткость фото и читаю страницу..."):
                try:
                    st.session_state.source_text = read_uploaded_photo(photo_file)
                    st.success("Страница успешно прочитана! Перейди на вкладку «Вставить текст» — текст уже там.")
                except Exception as e:
                    st.error(f"Не удалось прочитать фото: {e}")

with tab_txt:
    text = st.text_area("Поле для текста:", value=st.session_state.source_text, height=180, placeholder="Вставь сюда любой параграф по истории, географии, математике, биологии или физике...", label_visibility="collapsed")
    st.session_state.source_text = text
