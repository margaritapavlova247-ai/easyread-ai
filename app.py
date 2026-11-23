import streamlit as st
import json, os, hashlib
from groq import Groq

# Вставь свой ключ gsk_... внутрь кавычек:
client = Groq(api_key=st.secrets.get("GROQ_API_KEY", ""))

st.set_page_config(page_title="EasyRead AI", page_icon="📖", layout="centered")

USERS_FILE, SESSION_FILE = "users_db.json", "saved_session.json"

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

if "current_user" not in st.session_state:
    st.session_state.current_user = load_json(SESSION_FILE, {}).get("username")
for key, val in (("adapted_text", ""), ("quiz_data", None), ("show_quiz", False), ("grade_result", None)):
    if key not in st.session_state: st.session_state[key] = val

st.markdown("""
    <style>
    @import url('https://googleapis.com');
    html, body, p, div, label, input, textarea, select, button {
        font-family: 'Nunito', sans-serif !important;
    }
    .auth-header {
        background: linear-gradient(135deg, #5B4BC4 0%, #8E7FF5 100%);
        padding: 40px 32px;
        border-radius: 26px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 16px 40px rgba(91, 75, 196, 0.22);
    }
    .auth-header h1 { font-size: 38px !important; font-weight: 900 !important; margin: 0 !important; }
    .auth-header p { font-size: 20px !important; margin-top: 12px !important; opacity: 0.95; }
    </style>
""", unsafe_allow_html=True)

if not st.session_state.current_user:
    st.markdown('<div class="auth-header" translate="no"><h1>EasyRead AI</h1><p>Личный кабинет ученика — войди или создай аккаунт</p></div>', unsafe_allow_html=True)
    tab_login, tab_reg = st.tabs(("Вход в аккаунт", "Регистрация"))

    with tab_login:
        with st.form("login_form"):
            nick = st.text_input("Никнейм:")
            pwd = st.text_input("Пароль:", type="password")
            rem = st.checkbox("Запомнить меня на этом устройстве", value=True)
            if st.form_submit_button("Войти в кабинет"):
                users = load_json(USERS_FILE, {})
                if nick in users and users.get(nick).get("password") == hash_pass(pwd):
                    st.session_state.current_user = nick
                    if rem: save_json(SESSION_FILE, {"username": nick})
                    st.rerun()
                else: st.error("Неверный никнейм или пароль.")

    with tab_reg:
        with st.form("reg_form"):
            r_nick = st.text_input("Придумай никнейм:")
            r_pwd = st.text_input("Придумай пароль (от 4 символов):", type="password")
            r_pwd2 = st.text_input("Повтори пароль:", type="password")
            r_rem = st.checkbox("Запомнить меня сразу", value=True)
            if st.form_submit_button("Создать аккаунт"):
                users = load_json(USERS_FILE, {})
                if not r_nick.strip() or len(r_pwd) < 4: st.warning("Введи никнейм и пароль (минимум 4 символа).")
                elif r_nick in users: st.error("Этот никнейм уже занят.")
                elif r_pwd != r_pwd2: st.error("Пароли не совпадают.")
                else:
                    users.update({r_nick: {"password": hash_pass(r_pwd)}})
                    save_json(USERS_FILE, users)
                    st.session_state.current_user = r_nick
                    if r_rem: save_json(SESSION_FILE, {"username": r_nick})
                    st.rerun()

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Google"): st.session_state.current_user = "Google_User"; save_json(SESSION_FILE, {"username": "Google_User"}); st.rerun()
    with c2:
        if st.button("Facebook"): st.session_state.current_user = "Facebook_User"; save_json(SESSION_FILE, {"username": "Facebook_User"}); st.rerun()
    with c3:
        if st.button("Apple"): st.session_state.current_user = "Apple_User"; save_json(SESSION_FILE, {"username": "Apple_User"}); st.rerun()
    st.stop()
with st.sidebar:
    st.markdown(f"<div style='font-size:24px; font-weight:800; margin-bottom:12px;'>Профиль: {st.session_state.current_user}</div>", unsafe_allow_html=True)
    if st.button("Выйти из аккаунта"):
        st.session_state.current_user = None
        if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
        st.rerun()
    st.markdown("<hr style='margin:24px 0;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:22px; font-weight:800; margin-bottom:10px;'>Оформление страницы</div>", unsafe_allow_html=True)
    theme = st.selectbox("Оттенок фона для глаз:", ("Мягкий кремовый", "Нежно-мятный", "Спокойный голубой"))
    font_size = st.slider("Размер текста результата:", min_value=18, max_value=28, value=22)

bg_color = "#F8F4EC" if "кремовый" in theme else ("#EDF6F1" if "мятный" in theme else "#ECF3FA")
accent_color = "#5B4BC4" if "кремовый" in theme else ("#0D8A72" if "мятный" in theme else "#2563EB")
accent_light = "#8E7FF5" if "кремовый" in theme else ("#34D399" if "мятный" in theme else "#60A5FA")

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: #1A1D26; }}
    .block-container {{ max-width: 840px !important; padding-top: 2.5rem !important; padding-bottom: 4rem !important; }}
    p, label, .stMarkdown p, .stRadio label p, .stSelectbox label p, .stSlider label p, .stTextArea label p {{
        font-size: 20px !important;
        line-height: 1.65 !important;
    }}
    div[role="radiogroup"] label {{
        background-color: #FFFFFF;
        padding: 14px 18px !important;
        border-radius: 14px !important;
        border: 1px solid rgba(0,0,0,0.06) !important;
        margin-bottom: 10px !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.02);
        transition: 0.2s;
    }}
    div[role="radiogroup"] label:hover {{
        border-color: {accent_color} !important;
        transform: translateX(4px);
    }}
    textarea {{
        font-size: 19px !important;
        line-height: 1.6 !important;
        border-radius: 16px !important;
        padding: 16px !important;
        border: 1.5px solid rgba(0,0,0,0.08) !important;
    }}
    .hero-box {{
        background: linear-gradient(135deg, {accent_color} 0%, {accent_light} 100%);
        padding: 38px 34px;
        border-radius: 26px;
        color: white;
        margin-bottom: 32px;
        box-shadow: 0 18px 40px rgba(0,0,0,0.1);
    }}
    .hero-badge {{
        display: inline-block;
        background: rgba(255,255,255,0.2);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 14px !important;
        font-weight: 800;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        margin-bottom: 12px;
    }}
    .hero-title {{ font-size: 40px !important; font-weight: 900 !important; margin: 0 !important; line-height: 1.15 !important; }}
    .hero-sub {{ font-size: 20px !important; opacity: 0.95; margin-top: 12px !important; }}
    .section-title {{ font-size: 25px !important; font-weight: 800 !important; color: #1A1D26; margin-top: 24px !important; margin-bottom: 12px !important; }}
    div.stVerticalBlockBorderWrapper {{
        background-color: #FFFFFF !important;
        border-radius: 22px !important;
        border: none !important;
        border-left: 7px solid {accent_color} !important;
        padding: 22px 26px !important;
        box-shadow: 0 12px 32px rgba(0,0,0,0.06) !important;
        margin: 18px 0 !important;
    }}
    div.stVerticalBlockBorderWrapper p {{ font-size: {font_size}px !important; line-height: 1.75 !important; margin-bottom: 14px !important; }}
    .a4-paper {{ background-color: #FFFFFF; padding: 32px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 14px 36px rgba(0,0,0,0.08); margin: 28px 0 18px 0; border-top: 9px solid {accent_color}; text-align: center; }}
    .grade-box {{ background-color: #FFF5F5; border: 3px solid #E02424; border-radius: 24px; padding: 30px; text-align: center; margin-top: 24px; box-shadow: 0 12px 30px rgba(224, 36, 36, 0.12); }}
    .grade-number {{ font-size: 80px !important; font-weight: 900 !important; color: #E02424; line-height: 1.1 !important; }}
    @keyframes shimmer {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}
    div.stButton > button {{
        background: linear-gradient(270deg, {accent_color}, {accent_light}, {accent_color});
        background-size: 200% 200%;
        animation: shimmer 5s ease infinite;
        color: white !important;
        font-size: 21px !important;
        font-weight: 800 !important;
        padding: 16px 28px !important;
        border-radius: 16px !important;
        border: none !important;
        width: 100%;
        margin-top: 10px !important;
        box-shadow: 0 8px 22px rgba(91, 75, 196, 0.25);
    }}
    </style>
""", unsafe_allow_html=True)
st.markdown(f"""
    <div class="hero-box" translate="no">
        <div class="hero-badge">Умный помощник для учёбы</div>
        <div class="hero-title">EasyRead AI</div>
        <div class="hero-sub">Привет, <b>{st.session_state.current_user}</b>! Вставь сложный параграф из учебника, и я оформлю его так, чтобы было легко читать и запоминать.</div>
    </div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-title">1. Исходный текст из учебника</div>', unsafe_allow_html=True)
text = st.text_area("Поле для текста:", height=180, placeholder="Вставь сюда любой параграф по истории, биологии, литературе или физике...", label_visibility="collapsed")

st.markdown('<div class="section-title">2. Выбери формат обработки</div>', unsafe_allow_html=True)
mode = st.radio(
    "Формат:",
    (
        "Упрощённый текст — короткие абзацы и выделение главного",
        "Главная суть — только даты, имена, термины и определения",
        "Объяснение простыми словами — с примером из жизни"
    ),
    label_visibility="collapsed"
)

if st.button("Адаптировать текст"):
    if text.strip():
        with st.spinner("Перестраиваю текст..."):
            if "Упрощённый" in mode:
                task = "Перепиши текст на русском языке максимально просто и понятно: разбей на короткие абзацы по 2 предложения, разделяй абзацы пустой строкой, убери сложные слова и воду, выдели **жирным шрифтом** ключевые слова. Не используй смайлики и эмодзи."
            elif "Главная суть" in mode:
                task = """Выпиши из этого текста на русском языке ТОЛЬКО самую главную суть: все важные даты, имена, термины и определения.
                Строгие правила оформления:
                1. Никаких смайликов и эмодзи.
                2. Каждый термин или дата ДОЛЖНЫ начинаться с нового абзаца (обязательно ставь пустую строку между пунктами).
                3. Формат каждого абзаца: **Дата или термин** — чёткое объяснение в 1-2 предложения.
                4. Никаких вступлений и заключений, только сам список."""
            else:
                task = "Объясни этот текст на русском языке максимально простыми и понятными словами, добавь 1 яркий пример из жизни. Разделяй абзацы пустой строкой. Не используй смайлики и эмодзи."

            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=({"role": "system", "content": "Ты помощник в учёбе. Работай строго по тексту пользователя. Никогда не используй эмодзи и смайлики."}, {"role": "user", "content": f"{task}\n\nТекст:\n{text}"})
            )
            st.session_state.adapted_text = response.choices.pop(0).message.content
            st.session_state.show_quiz = False
            st.session_state.grade_result = None
    else:
        st.warning("Сначала вставь текст в поле выше.")

if st.session_state.adapted_text:
    st.markdown('<div class="section-title">3. Готовый материал</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(st.session_state.adapted_text)
    if st.button("Создать контрольный тест (5 заданий)"):
        with st.spinner("Составляю контрольную работу..."):
            quiz_prompt = f"""Составь контрольную на русском из 5 заданий по тексту без смайликов. Верни СТРОГО валидный JSON без ```json:
            {{"q1": {{"question": "Вопрос 1?", "options": ["А", "Б", "В"]}}, "q2": {{"question": "Вопрос 2?", "options": ["А", "Б", "В"]}}, "q3": {{"question": "Вопрос 3?", "options": ["А", "Б", "В"]}}, "q4": {{"title": "Задание 4: Соедини пару", "left_1": "Элемент 1", "left_2": "Элемент 2", "right_options": ["Пара 1", "Пара 2"]}}, "q5": "Задание 5 (Мини-эссе): Перескажи тему в 2-3 предложениях."}}
            Текст: {text}"""
            q_resp = client.chat.completions.create(model="openai/gpt-oss-120b", messages=({"role": "user", "content": quiz_prompt},))
            raw_json = q_resp.choices.pop(0).message.content.strip().strip("`").replace("json", "", 1).strip()
            try:
                st.session_state.quiz_data = json.loads(raw_json)
                st.session_state.show_quiz = True
                st.session_state.grade_result = None
            except Exception:
                st.error("Нажми на кнопку «Создать контрольный тест» ещё раз.")

if st.session_state.show_quiz and st.session_state.quiz_data:
    qd = st.session_state.quiz_data
    st.markdown('<div class="a4-paper"><h2 style="margin:0; font-weight:900;">КОНТРОЛЬНАЯ РАБОТА</h2><p style="margin-top:6px; color:#64748B;">Ответь на вопросы, соедини пары и напиши мини-эссе</p></div>', unsafe_allow_html=True)
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
            with st.spinner("Проверяю ответы..."):
                check_prompt = f"""Проверь контрольную по тексту: {text}. Ответы: 1){ans1}, 2){ans2}, 3){ans3}, 4){qd.get('q4').get('left_1')}={match1}, {qd.get('q4').get('left_2')}={match2}, 5)Эссе: {essay}. Без смайликов.
                Верни СТРОГО JSON без ```json: {{"grade": 9, "feedback": "Разбор по пунктам на русском с пустыми строками между абзацами"}}"""
                c_resp = client.chat.completions.create(model="openai/gpt-oss-120b", messages=({"role": "user", "content": check_prompt},))
                raw_check = c_resp.choices.pop(0).message.content.strip().strip("`").replace("json", "", 1).strip()
                try: st.session_state.grade_result = json.loads(raw_check)
                except Exception: st.error("Ошибка проверки, нажми ещё раз.")

if st.session_state.grade_result:
    gr = st.session_state.grade_result
    st.markdown(f'<div class="grade-box"><div style="color:#C53030; font-weight:800; font-size:20px;">ТВОЯ ОЦЕНКА ЗА РАБОТУ</div><div class="grade-number">{gr.get("grade")} / 10</div></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(gr.get("feedback"))
    if st.button("Окей, закрыть разбор"):
        st.session_state.show_quiz = False
        st.session_state.grade_result = None
        st.rerun()
