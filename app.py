import streamlit as st
import json, os, hashlib, hmac, base64, io
import urllib.request, urllib.parse
from datetime import datetime
from PIL import Image, ImageEnhance, ImageOps
from groq import Groq

GROQ_KEY = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
SB_URL = st.secrets.get("SUPABASE_URL", "").rstrip("/") if hasattr(st, "secrets") else ""
SB_KEY = st.secrets.get("SUPABASE_KEY", "") if hasattr(st, "secrets") else ""

client = Groq(api_key=GROQ_KEY)

st.set_page_config(page_title="StudyBox", page_icon="🌿", layout="centered")

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

    uploaded_file.seek(0)
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    max_side = max(w, h)
    if max_side < 1800:
        scale = 1800 / max_side
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    elif max_side > 2400:
        scale = 2400 / max_side
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = ImageEnhance.Sharpness(img).enhance(1.6)

    raw_text = pytesseract.image_to_string(img, lang="rus+ron+eng", config="--psm 6").strip()
    if not raw_text:
        raise Exception("На фото не удалось найти текст. Попробуй сфотографировать страницу ближе и ровнее.")

    clean_resp = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=(
            {"role": "system", "content": "Ты опытный школьный учитель математики и корректор. Тебе дают текст, отсканированный со страницы школьного учебника (на русском или румынском языке). В тексте могут быть опечатки сканера в словах и математических формулах (дроби, степени, корни, уравнения). Восстанови по смыслу все слова и математические выражения, запиши формулы аккуратно (например, a/b, x^2, √x), убери случайный мусор из букв, сохраняя весь исходный текст параграфа слово в слово. Не добавляй своих комментариев — верни ТОЛЬКО восстановленный чистый текст страницы."},
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
    ("show_new_nb_form", False),
    ("input_tab", "Вставить текст")
)
for key, val in defaults:
    if key not in st.session_state:
        st.session_state[key] = val

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
    html, body, p, div, label, input, textarea, select, button { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    .stApp {
        background-color: #F5F6EA;
        background-image: radial-gradient(circle at 12% 10%, rgba(174, 186, 101, 0.18) 0%, transparent 38%),
                          radial-gradient(circle at 88% 85%, rgba(110, 126, 62, 0.12) 0%, transparent 42%);
        color: #232816;
    }
    .auth-card {
        background: linear-gradient(135deg, #6E7E3E 0%, #99A754 55%, #AEBA65 100%);
        padding: 42px 34px; border-radius: 28px; color: #FFFFFF; text-align: center;
        margin-bottom: 28px; box-shadow: 0 20px 45px rgba(110, 126, 62, 0.24);
        border: 1px solid rgba(255,255,255,0.3); position: relative; overflow: hidden;
    }
    .auth-pill {
        display: inline-block; background: rgba(255,255,255,0.22); backdrop-filter: blur(6px);
        padding: 6px 16px; border-radius: 999px; font-size: 13px !important; font-weight: 700;
        letter-spacing: 1px; text-transform: uppercase; margin-bottom: 14px;
    }
    .auth-card h1 { font-family: 'Lora', serif !important; font-size: 42px !important; font-weight: 700 !important; margin: 0 !important; }
    .auth-card p { font-size: 18px !important; margin-top: 10px !important; opacity: 0.95; }
    div.stFormSubmitButton > button {
        background: #6E7E3E !important; color: #FFFFFF !important; font-weight: 700 !important;
        border-radius: 14px !important; border: none !important; padding: 12px 24px !important;
        font-size: 17px !important; transition: all 0.2s ease; box-shadow: 0 6px 16px rgba(110, 126, 62, 0.22);
    }
    div.stFormSubmitButton > button:hover { background: #5B6931 !important; transform: translateY(-1px); }
    </style>
""", unsafe_allow_html=True)

if not st.session_state.current_user:
    st.markdown('<div class="auth-card" translate="no"><div class="auth-pill">Digital Study Space</div><h1>StudyBox</h1><p>Умные конспекты, облачные тетради и проверка знаний без стресса</p></div>', unsafe_allow_html=True)
    tab_login, tab_reg = st.tabs(("Вход в кабинет", "Создать аккаунт"))

    with tab_login:
        with st.form("login_form"):
            nick = st.text_input("Никнейм:")
            pwd = st.text_input("Пароль:", type="password")
            rem = st.checkbox("Запомнить меня на этом устройстве", value=True)
            if st.form_submit_button("Войти в StudyBox"):
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
            if st.form_submit_button("Зарегистрироваться"):
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
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #6E7E3E 0%, #8E9E52 100%); padding: 18px 20px; border-radius: 18px; color: white; margin-bottom: 14px; box-shadow: 0 8px 20px rgba(110,126,62,0.18);">
            <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.85; font-weight: 700;">Ученик</div>
            <div style="font-size: 21px; font-weight: 800; margin-top: 2px;">{st.session_state.current_user}</div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("Выйти из аккаунта", key="logout_btn"):
        st.session_state.current_user = None
        st.session_state.active_notebook = None
        st.session_state.source_text = ""
        st.session_state.adapted_text = ""
        st.query_params.clear()
        st.rerun()

    st.markdown("<hr style='margin:16px 0; border-color: rgba(110, 126, 62, 0.22);'>", unsafe_allow_html=True)

    if st.button("Новый конспект", key="home_btn"):
        st.session_state.active_notebook = None
        st.rerun()

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    col_title, col_plus = st.columns((4, 1))
    with col_title:
        st.markdown("<div style='font-size:16px; font-weight:800; text-transform:uppercase; letter-spacing:0.8px; color:#55632D; padding-top:8px;'>Мои тетради</div>", unsafe_allow_html=True)
    with col_plus:
        if st.button("+", key="add_nb_btn", help="Создать новую тетрадь"):
            st.session_state.show_new_nb_form = not st.session_state.show_new_nb_form

    if st.session_state.show_new_nb_form:
        with st.form("new_nb_form"):
            new_nb_name = st.text_input("Название тетради:", placeholder="Например: Алгебра")
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
        label_text = f"{nb_name}  ·  {notes_count}" if notes_count > 0 else nb_name
        if st.button(label_text, key=f"nb_btn_{nb_name}"):
            st.session_state.active_notebook = nb_name
            st.rerun()

st.markdown("""
    <style>
    section[data-testid="stSidebar"] {
        background-color: #ECEED6 !important;
        border-right: 1px solid rgba(110, 126, 62, 0.22);
    }
    .block-container { max-width: 800px !important; padding-top: 2rem !important; padding-bottom: 4.5rem !important; }
    p, label, .stMarkdown p, .stRadio label p, .stSelectbox label p, .stTextArea label p, .stTextInput label p {
        font-size: 18px !important; line-height: 1.65 !important; color: #232816;
    }
    .hero-banner {
        background: linear-gradient(135deg, #6E7E3E 0%, #96A552 60%, #AEBA65 100%);
        padding: 36px 34px; border-radius: 28px; color: #FFFFFF; margin-bottom: 28px;
        box-shadow: 0 18px 42px rgba(110, 126, 62, 0.22);
        border: 1px solid rgba(255,255,255,0.28);
    }
    .hero-banner p, .hero-banner div, .hero-banner h1 { color: #FFFFFF !important; }
    .hero-chip {
        display: inline-block; background: rgba(255,255,255,0.22); backdrop-filter: blur(6px);
        padding: 5px 14px; border-radius: 999px; font-size: 12px !important; font-weight: 700;
        letter-spacing: 1.1px; text-transform: uppercase; margin-bottom: 12px;
    }
    .hero-heading { font-family: 'Lora', serif !important; font-size: 40px !important; font-weight: 700 !important; margin: 0 !important; line-height: 1.15 !important; }
    .hero-desc { font-size: 18px !important; opacity: 0.95; margin-top: 10px !important; max-width: 640px; }
    .step-header {
        display: flex; align-items: center; gap: 10px; margin-bottom: 8px;
    }
    .step-pill {
        background-color: #6E7E3E; color: #FFFFFF !important; font-size: 12px !important; font-weight: 800;
        padding: 4px 11px; border-radius: 999px; letter-spacing: 0.8px; text-transform: uppercase;
    }
    .step-title {
        font-family: 'Lora', serif !important; font-size: 24px !important; font-weight: 700 !important; color: #2C331A !important;
    }
    div.stVerticalBlockBorderWrapper {
        background-color: #FCFDF8 !important; border-radius: 24px !important;
        border: 1.5px solid #D6D794 !important;
        padding: 24px 28px !important;
        box-shadow: 0 12px 32px rgba(110, 126, 62, 0.08) !important;
        margin: 16px 0 !important;
    }
    div.stVerticalBlockBorderWrapper p { font-size: 19px !important; line-height: 1.75 !important; color: #232816 !important; }
    div[role="radiogroup"] label {
        background-color: #F6F7EB; padding: 13px 18px !important; border-radius: 14px !important;
        border: 1.5px solid #D6D794 !important; margin-bottom: 10px !important;
        transition: all 0.18s ease;
    }
    div[role="radiogroup"] label:hover {
        border-color: #6E7E3E !important; background-color: #EEF0DA !important; transform: translateX(4px);
    }
    textarea, input[type="text"] {
        font-size: 17px !important; border-radius: 16px !important; padding: 15px !important;
        background-color: #F7F8ED !important; border: 1.5px solid #D6D794 !important; color: #232816 !important;
    }
    textarea:focus, input[type="text"]:focus {
        border-color: #6E7E3E !important; background-color: #FFFFFF !important;
        box-shadow: 0 0 0 3px rgba(110, 126, 62, 0.16) !important;
    }
    .exam-sheet {
        background-color: #FCFDF8; padding: 30px; border-radius: 22px; border: 1.5px solid #D6D794;
        box-shadow: 0 14px 34px rgba(110, 126, 62, 0.1); margin: 28px 0 18px 0;
        border-top: 8px solid #6E7E3E; text-align: center;
    }
    .exam-sheet h2 { font-family: 'Lora', serif !important; color: #2C331A !important; }
    .result-badge-card {
        background: linear-gradient(135deg, #FCFDF8 0%, #EFF1DC 100%);
        border: 2px solid #6E7E3E; border-radius: 26px;
        padding: 30px; text-align: center; margin-top: 24px;
        box-shadow: 0 14px 32px rgba(110, 126, 62, 0.14);
    }
    .result-score { font-family: 'Lora', serif !important; font-size: 74px !important; font-weight: 700 !important; color: #55632D; line-height: 1.1 !important; }
    section.main div.stButton > button {
        background: linear-gradient(135deg, #6E7E3E 0%, #8A9A4F 100%) !important;
        color: #FFFFFF !important; font-size: 18px !important; font-weight: 700 !important;
        padding: 13px 22px !important; border-radius: 15px !important; border: none !important;
        width: 100%; margin-top: 6px !important; transition: all 0.2s ease;
        box-shadow: 0 8px 20px rgba(110, 126, 62, 0.22);
    }
    section.main div.stButton > button:hover {
        background: linear-gradient(135deg, #5C6B32 0%, #788842 100%) !important;
        transform: translateY(-1px); box-shadow: 0 10px 24px rgba(110, 126, 62, 0.28);
    }
    section.main div.stButton > button p { color: #FFFFFF !important; font-weight: 700 !important; }
    section[data-testid="stSidebar"] div.stButton > button {
        background: rgba(255, 255, 255, 0.55) !important; color: #232816 !important;
        font-size: 16px !important; font-weight: 600 !important; padding: 9px 14px !important;
        border-radius: 12px !important; border: 1px solid rgba(110, 126, 62, 0.2) !important;
        box-shadow: none !important; text-align: left !important; justify-content: flex-start !important;
        margin-top: 3px !important; margin-bottom: 3px !important; width: 100%; transition: 0.15s;
    }
    section[data-testid="stSidebar"] div.stButton > button p { color: #232816 !important; }
    section[data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #D6D794 !important; border-color: #6E7E3E !important;
    }
    </style>
""", unsafe_allow_html=True)
if st.session_state.active_notebook:
    nb_title = st.session_state.active_notebook
    st.markdown(f"""
        <div class="hero-banner" translate="no">
            <div class="hero-chip">Личная тетрадь</div>
            <div class="hero-heading">{nb_title}</div>
            <div class="hero-desc">Все твои сохранённые конспекты по этому предмету. Нажми на любую тему, чтобы повторить материал.</div>
        </div>
    """, unsafe_allow_html=True)

    saved_notes = notebooks.get(nb_title, ())
    if not saved_notes:
        st.info("В этой тетради пока пусто. Перейди на «Новый конспект», создай материал и нажми «Сохранить в тетрадь».")
    else:
        for idx, note in enumerate(saved_notes):
            with st.expander(f"{note.get('topic', 'Без названия')}  ·  {note.get('date', '')}"):
                st.markdown(note.get("content", ""))
                if st.button("Удалить этот конспект", key=f"del_{nb_title}_{idx}"):
                    updated_list = list(saved_notes)
                    updated_list.pop(idx)
                    notebooks.update({nb_title: updated_list})
                    save_user_notebooks(st.session_state.current_user, notebooks)
                    st.rerun()
    st.stop()

st.markdown(f"""
    <div class="hero-banner" translate="no">
        <div class="hero-chip">Smart Study Assistant</div>
        <div class="hero-heading">StudyBox</div>
        <div class="hero-desc">Привет, <b>{st.session_state.current_user}</b>! Вставь параграф или загрузи фото страницы учебника — я соберу понятный конспект и проверю твои знания.</div>
    </div>
""", unsafe_allow_html=True)

with st.container(border=True):
    col_sec1, col_clr = st.columns((3, 1))
    with col_sec1:
        st.markdown('<div class="step-header"><span class="step-pill">Шаг 01</span><span class="step-title">Материал из учебника</span></div>', unsafe_allow_html=True)
    with col_clr:
        if st.button("Очистить", key="clear_text_btn"):
            st.session_state.source_text = ""
            st.session_state.adapted_text = ""
            st.session_state.show_quiz = False
            st.session_state.grade_result = None
            st.rerun()

    tab_idx = 0 if st.session_state.input_tab == "Вставить текст" else 1
    input_mode = st.radio(
        "Способ ввода:",
        ("Вставить текст", "Загрузить или сфоткать страницу"),
        index=tab_idx,
        horizontal=True,
        label_visibility="collapsed"
    )
    st.session_state.input_tab = input_mode

    if input_mode == "Загрузить или сфоткать страницу":
        photo_file = st.file_uploader("Выбери фото страницы учебника или сделай снимок на телефоне:", type=("jpg", "jpeg", "png"))
        if photo_file is not None:
            st.image(photo_file, caption="Загруженная страница", use_container_width=True)
            if st.button("Распознать текст с фото", key="ocr_upload_btn"):
                with st.spinner("Улучшаю чёткость фото и читаю страницу..."):
                    try:
                        st.session_state.source_text = read_uploaded_photo(photo_file)
                        st.session_state.input_tab = "Вставить текст"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Не удалось прочитать фото: {e}")

    if input_mode == "Вставить текст":
        text = st.text_area("Поле для текста:", value=st.session_state.source_text, height=180, placeholder="Вставь сюда любой параграф по истории, географии, математике, биологии или физике...", label_visibility="collapsed")
        st.session_state.source_text = text
with st.container(border=True):
    st.markdown('<div class="step-header"><span class="step-pill">Шаг 02</span><span class="step-title">Формат конспекта</span></div>', unsafe_allow_html=True)
    mode = st.radio(
        "Формат:",
        (
            "Упрощённый текст — короткие абзацы и выделение главного",
            "Главная суть — только даты, имена, термины и определения",
            "Объяснение простыми словами — с примером из жизни"
        ),
        label_visibility="collapsed"
    )

    if st.button("Создать конспект", key="adapt_btn"):
        current_text = st.session_state.source_text.strip()
        if current_text:
            with st.spinner("Собираю красивый конспект..."):
                if "Упрощённый" in mode:
                    task = "Перепиши текст на русском языке максимально просто и понятно: разбей на короткие абзацы по 2 предложения, разделяй абзацы пустой строкой, убери сложные слова и воду, выдели **жирным шрифтом** ключевые слова. Не используй смайлики и эмодзи."
                elif "Главная суть" in mode:
                    task = """Выпиши из этого текста на русском языке ТОЛЬКО самую главную суть: все важные даты, имена, формулы, термины и определения.
                    Строгие правила оформления:
                    1. Никаких смайликов и эмодзи.
                    2. Каждый термин или дата ДОЛЖНЫ начинаться с нового абзаца (обязательно ставь пустую строку между пунктами).
                    3. Формат каждого абзаца: **Дата или термин** — чёткое объяснение в 1-2 предложения.
                    4. Никаких вступлений и заключений, только сам список."""
                else:
                    task = "Объясни этот текст на русском языке максимально простыми и понятными словами, добавь 1 яркий пример из жизни. Разделяй абзацы пустой строкой. Не используй смайлики и эмодзи."

                response = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=({"role": "system", "content": "Ты помощник в учёбе. Работай строго по тексту пользователя. Никогда не используй эмодзи и смайлики."}, {"role": "user", "content": f"{task}\n\nТекст:\n{current_text}"})
                )
                st.session_state.adapted_text = response.choices.pop(0).message.content
                st.session_state.show_quiz = False
                st.session_state.grade_result = None
        else:
            st.warning("Сначала вставь текст или распознай его с фотографии выше.")

if st.session_state.adapted_text:
    with st.container(border=True):
        st.markdown('<div class="step-header"><span class="step-pill">Шаг 03</span><span class="step-title">Готовый материал</span></div>', unsafe_allow_html=True)
        st.markdown(st.session_state.adapted_text)

        with st.expander("Сохранить этот конспект в тетрадь"):
            with st.form("save_note_form"):
                note_topic = st.text_input("Название темы:", placeholder="Например: Геометрия треугольника")
                target_nb = st.selectbox("В какую тетрадь сохранить:", tuple(notebooks.keys()))
                if st.form_submit_button("Сохранить в тетрадь"):
                    clean_topic = note_topic.strip() if note_topic.strip() else "Конспект без названия"
                    nb_list = list(notebooks.get(target_nb, ()))
                    nb_list.append({
                        "topic": clean_topic,
                        "content": st.session_state.adapted_text,
                        "date": datetime.now().strftime("%d.%m.%Y")
                    })
                    notebooks.update({target_nb: nb_list})
                    save_user_notebooks(st.session_state.current_user, notebooks)
                    st.success(f"Конспект «{clean_topic}» сохранён в тетрадь «{target_nb}»!")

        if st.button("Пройти контрольный тест (5 заданий)", key="make_quiz_btn"):
            saved_topic_text = st.session_state.source_text.strip() or st.session_state.adapted_text.strip()
            with st.spinner("Составляю контрольную работу..."):
                quiz_prompt = f"""Составь контрольную на русском языке из 5 заданий строго по этому тексту без смайликов. Верни СТРОГО валидный JSON без ```json:
                {{"q1": {{"question": "Вопрос 1?", "options": ["А", "Б", "В"]}}, "q2": {{"question": "Вопрос 2?", "options": ["А", "Б", "В"]}}, "q3": {{"question": "Вопрос 3?", "options": ["А", "Б", "В"]}}, "q4": {{"title": "Задание 4: Соедини пару", "left_1": "Элемент 1", "left_2": "Элемент 2", "right_options": ["Пара 1", "Пара 2"]}}, "q5": "Задание 5 (Мини-эссе): Перескажи тему в 2-3 предложениях."}}
                Текст: {saved_topic_text}"""
                q_resp = client.chat.completions.create(model="openai/gpt-oss-120b", messages=({"role": "user", "content": quiz_prompt},))
                raw_json = q_resp.choices.pop(0).message.content.strip().strip("`").replace("json", "", 1).strip()
                try:
                    parsed_q = json.loads(raw_json)
                    parsed_q.update({"_topic_text": saved_topic_text})
                    st.session_state.quiz_data = parsed_q
                    st.session_state.show_quiz = True
                    st.session_state.grade_result = None
                except Exception:
                    st.error("Нажми на кнопку «Пройти контрольный тест» ещё раз.")

if st.session_state.show_quiz and st.session_state.quiz_data:
    qd = st.session_state.quiz_data
    st.markdown('<div class="exam-sheet"><h2 style="margin:0; font-weight:700;">Контрольная работа</h2><p style="margin-top:6px; color:#55632D;">Ответь на вопросы, соедини пары и напиши мини-эссе</p></div>', unsafe_allow_html=True)
    with st.form("control_work_form"):
        ans1 = st.radio(f"1. {qd.get('q1').get('question')}", qd.get('q1').get('options'), key="r1")
        ans2 = st.radio(f"2. {qd.get('q2').get('question')}", qd.get('q2').get('options'), key="r2")
        ans3 = st.radio(f"3. {qd.get('q3').get('question')}", qd.get('q3').get('options'), key="r3")
        st.markdown(f"**{qd.get('q4').get('title')}**")
        c1, c2 = st.columns(2)
        with c1: match1 = st.selectbox(qd.get('q4').get('left_1'), qd.get('q4').get('right_options'), key="m1")
        with c2: match2 = st.selectbox(qd.get('q4').get('left_2'), qd.get('q4').get('right_options'), key="m2")
        essay = st.text_area(f"5. {qd.get('q5')}", height=110)
        if st.form_submit_button("Отправить на проверку"):
            topic_for_check = qd.get("_topic_text") or st.session_state.source_text.strip() or st.session_state.adapted_text.strip()
            with st.spinner("Внимательно проверяю каждый ответ по теме..."):
                check_prompt = f"""Ты строгий, но справедливый школьный учитель. Проверь контрольную работу ученика СТРОГО по данному ниже исходному тексту и заданным вопросам. Не придумывай факты не из текста. Без смайликов.

ИСХОДНЫЙ ТЕКСТ ТЕМЫ:
{topic_for_check}

ВОПРОСЫ И ОТВЕТЫ УЧЕНИКА:
1. Вопрос: {qd.get('q1').get('question')} | Ответ ученика: {ans1}
2. Вопрос: {qd.get('q2').get('question')} | Ответ ученика: {ans2}
3. Вопрос: {qd.get('q3').get('question')} | Ответ ученика: {ans3}
4. Соединить пары: {qd.get('q4').get('left_1')} -> ученик выбрал «{match1}»; {qd.get('q4').get('left_2')} -> ученик выбрал «{match2}»
5. {qd.get('q5')} | Мини-эссе ученика: «{essay}»

Оцени работу по 10-балльной шкале (от 1 до 10) и разбери каждый из 5 пунктов отдельно (верно или нет, и почему).
Верни СТРОГО валидный JSON без ```json: {{"grade": 9, "feedback": "Подробный разбор каждого из 5 заданий на русском языке с пустыми строками между пунктами"}}"""
                c_resp = client.chat.completions.create(model="openai/gpt-oss-120b", messages=({"role": "user", "content": check_prompt},))
                raw_check = c_resp.choices.pop(0).message.content.strip().strip("`").replace("json", "", 1).strip()
                try:
                    st.session_state.grade_result = json.loads(raw_check)
                except Exception:
                    st.error("Ошибка проверки, нажми на кнопку «Отправить на проверку» ещё раз.")

if st.session_state.grade_result:
    gr = st.session_state.grade_result
    st.markdown(f'<div class="result-badge-card"><div style="color:#55632D; font-weight:800; font-size:15px; letter-spacing:1px; text-transform:uppercase;">Оценка за работу</div><div class="result-score">{gr.get("grade")} / 10</div></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(gr.get("feedback"))
    if st.button("Закрыть разбор", key="close_grade_btn"):
        st.session_state.show_quiz = False
        st.session_state.grade_result = None
        st.rerun()
