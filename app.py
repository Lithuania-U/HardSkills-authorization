import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import base64
from datetime import datetime

# Importuoti autorizacijos funkcijas (jei sukūrėte auth.py failą)
# from auth import auth_wrapper, save_current_assessment
# Arba tiesiog pridėkite visas auth funkcijas čia viršuje

# === AUTH SISTEMA (nukopijuokite iš pirmojo artefakto) ===
import hashlib
import sqlite3

DB_PATH = "skills_users.db"

def init_database():
    """Sukurti vartotojų duomenų bazę"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Vartotojų lentelė
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            username TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Įgūdžių vertinimų lentelė
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skill_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            assessment_data TEXT,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hash):
    return hash_password(password) == hash

def create_user(email, password, username):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute('INSERT INTO users (email, password_hash, username) VALUES (?, ?, ?)', 
                      (email, password_hash, username))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        return None

def authenticate_user(email, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, password_hash, username FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user and verify_password(password, user[1]):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user[0],))
        conn.commit()
        conn.close()
        return {'id': user[0], 'username': user[2], 'email': email}
    return None

def save_skill_assessment(user_id, skills_data, comment=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    assessment_json = json.dumps(skills_data)
    cursor.execute('INSERT INTO skill_assessments (user_id, assessment_data, comment) VALUES (?, ?, ?)', 
                  (user_id, assessment_json, comment))
    conn.commit()
    assessment_id = cursor.lastrowid
    conn.close()
    return assessment_id

def get_user_assessments(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''SELECT id, assessment_data, comment, created_at 
                     FROM skill_assessments WHERE user_id = ? ORDER BY created_at DESC''', (user_id,))
    assessments = []
    for row in cursor.fetchall():
        assessments.append({
            'id': row[0],
            'data': json.loads(row[1]),
            'comment': row[2],
            'created_at': row[3]
        })
    conn.close()
    return assessments

# === PAGRINDINĖ APP KONFIGŪRACIJA ===

st.set_page_config(
    page_title="Įgūdžių Radar", 
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🎯"
)

# Kampų žemėlapis
angles = {
    0: "MATEMATIKA, KVANTINĖ FIZIKA",
    10: "DIRBTINIS INTELEKTAS, MAŠINŲ MOKYMAS",
    20: "FIZIKA, ELEKTRONIKA, KOMPIUTERIJA",
    30: "INŽINERIJA",
    40: "ELEKTROTECHNIKA",
    50: "MECHANIKA",
    60: "ARCHITEKTŪRA, MODELIAVIMAS",
    70: "STATISTIKA, DUOMENYS",
    80: "FINANSAI, EKONOMIKA",
    90: "ĮSTATYMAI, TEISĖ",
    100: "POLITIKA",
    110: "VALDŽIA, VALSTYBĖ",
    120: "RAŠTAS, SKAIČIAI",
    130: "AMATAI, PREKYBA",
    140: "RELIGIJOS",
    150: "BŪSTAS, STATYBA",
    160: "KELIONĖS, ATRADIMAI",
    170: "AGRESIJA, DOMINAVIMAS",
    180: "FIZINĖ JĖGA",
    190: "MAISTAS",
    200: "SEKSAS, VAIKAI",
    210: "ŠILUMA, BUITIS",
    220: "VALGIO RUOŠIMAS",
    230: "GLOBA/RŪPYBA",
    240: "EMPATIJA",
    250: "PUOŠYBA",
    260: "MUZIKA, ŠOKIS",
    270: "DRAMATIKA, GINČAI",
    280: "LITERATŪRA",
    290: "MEDIA, DIZAINAS",
    300: "ISTORIJA, ŽURNALISTIKA",
    310: "PSICHOLOGIJA",
    320: "MĄSTYMAS, FILOSOFIJA",
    330: "BIOLOGIJA, NEUROMOKSLAI",
    340: "MEDICINOS MOKSLAI",
    350: "CHEMIJA, BIOTECHNOLOGIJOS",
}

st.session_state.angles = angles

# === AUTORIZACIJOS SISTEMA ===

def login_form():
    st.subheader("🔐 Prisijungimas")
    with st.form("login_form"):
        email = st.text_input("El. paštas")
        password = st.text_input("Slaptažodis", type="password")
        submit_button = st.form_submit_button("Prisijungti")
        
        if submit_button:
            if email and password:
                user = authenticate_user(email, password)
                if user:
                    st.session_state.user = user
                    st.success(f"Sveiki sugrįžę, {user['username']}! 👋")
                    st.rerun()
                else:
                    st.error("Neteisingas el. paštas arba slaptažodis!")
            else:
                st.error("Prašome užpildyti visus laukus!")

def register_form():
    st.subheader("📝 Registracija")
    with st.form("register_form"):
        username = st.text_input("Vartotojo vardas")
        email = st.text_input("El. paštas")
        password = st.text_input("Slaptažodis", type="password")
        password_confirm = st.text_input("Patvirtinkite slaptažodį", type="password")
        submit_button = st.form_submit_button("Registruotis")
        
        if submit_button:
            if username and email and password and password_confirm:
                if password != password_confirm:
                    st.error("Slaptažodžiai nesutampa!")
                elif len(password) < 6:
                    st.error("Slaptažodis turi būti bent 6 simbolių ilgio!")
                else:
                    user_id = create_user(email, password, username)
                    if user_id:
                        st.success("Registracija sėkminga! Dabar galite prisijungti.")
                        st.rerun()
                    else:
                        st.error("Vartotojas su tokiu el. paštu jau egzistuoja!")
            else:
                st.error("Prašome užpildyti visus laukus!")

# === PAGRINDINĖ APLIKACIJA ===

def create_radar_chart(skills_data):
    """Sukurti radar diagramą"""
    # Paruošti duomenis
    categories = []
    values = []
    
    for angle in sorted(skills_data.keys()):
        categories.append(angles.get(int(angle), f"Kampas {angle}"))
        values.append(skills_data[angle])
    
    # Sukurti polar chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        fillcolor='rgba(0, 123, 255, 0.3)',
        line=dict(color='rgb(0, 123, 255)', width=3),
        marker=dict(size=8, color='rgb(0, 123, 255)'),
        name='Įgūdžiai'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10],
                tickfont=dict(size=12),
                gridcolor='lightgray'
            ),
            angularaxis=dict(
                tickfont=dict(size=10),
                rotation=90,
                direction="clockwise"
            )
        ),
        showlegend=False,
        title={
            'text': "Jūsų įgūdžių radar",
            'x': 0.5,
            'font': {'size': 20}
        },
        width=800,
        height=800
    )
    
    return fig

def main_app():
    """Pagrindinė aplikacija prisijungusiems vartotojams"""
    
    # Viršutinė juosta su vartotojo info
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.title("🎯 Įgūdžių įsivertinimas")
        st.write(f"Sveiki, **{st.session_state.user['username']}**!")
    
    with col2:
        if st.button("👤 Profilis", type="secondary"):
            st.session_state.show_profile = True
        if st.button("🚪 Atsijungti", type="secondary"):
            del st.session_state.user
            st.rerun()
    
    # Tikrinti ar rodyti profilį
    if st.session_state.get('show_profile', False):
        show_profile()
        return
    
    # Pagrindinis vertinimo interface
    st.subheader("Įvertinkite savo įgūdžius skalėje nuo 1 iki 10")
    
    # Sidebar su įgūdžių sąrašu
    with st.sidebar:
        st.header("🎯 Įgūdžių kategorijos")
        skills_data = {}
        
        for angle, skill_name in angles.items():
            skills_data[angle] = st.slider(
                skill_name,
                min_value=1,
                max_value=10,
                value=5,
                key=f"skill_{angle}"
            )
    
    # Pagrindinis turinys
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Rodyti radar diagramą
        if skills_data:
            fig = create_radar_chart(skills_data)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Statistikos")
        avg_score = sum(skills_data.values()) / len(skills_data)
        max_skill = max(skills_data.items(), key=lambda x: x[1])
        min_skill = min(skills_data.items(), key=lambda x: x[1])
        
        st.metric("Vidutinis balas", f"{avg_score:.1f}")
        st.write(f"**Stipriausia:** {angles[max_skill[0]]} ({max_skill[1]}/10)")
        st.write(f"**Silpniausia:** {angles[min_skill[0]]} ({min_skill[1]}/10)")
        
        st.divider()
        
        st.subheader("💾 Išsaugoti vertinimą")
        comment = st.text_area("Pridėti komentarą (neprivaloma)")
        
        if st.button("💾 Išsaugoti", type="primary"):
            assessment_id = save_skill_assessment(
                st.session_state.user['id'],
                skills_data,
                comment
            )
            st.success(f"Vertinimas išsaugotas! ID: {assessment_id}")
            
        st.divider()
        
        # Eksporto mygtukai
        st.subheader("📥 Eksportuoti")
        
        # JSON eksportas
        if st.button("📄 Atsisiųsti JSON"):
            json_data = {
                "user": st.session_state.user['username'],
                "timestamp": datetime.now().isoformat(),
                "skills": skills_data,
                "comment": comment
            }
            json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="💾 JSON failas",
                data=json_str,
                file_name=f"skills_{st.session_state.user['username']}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )

def show_profile():
    """Rodyti vartotojo profilį"""
    if st.button("⬅️ Grįžti į vertinimą"):
        st.session_state.show_profile = False
        st.rerun()
    
    st.header(f"👤 {st.session_state.user['username']} profilis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write(f"**El. paštas:** {st.session_state.user['email']}")
        st.write(f"**Vartotojo ID:** {st.session_state.user['id']}")
    
    st.divider()
    st.subheader("📊 Jūsų įgūdžių istorija")
    
    assessments = get_user_assessments(st.session_state.user['id'])
    
    if assessments:
        for i, assessment in enumerate(assessments):
            with st.expander(f"Vertinimas #{len(assessments)-i} - {assessment['created_at'][:16]}"):
                if assessment['comment']:
                    st.write(f"**Komentaras:** {assessment['comment']}")
                
                # Mini radar diagrama
                fig = create_radar_chart(assessment['data'])
                fig.update_layout(width=400, height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # Statistikos
                avg_score = sum(assessment['data'].values()) / len(assessment['data'])
                st.write(f"**Vidutinis balas:** {avg_score:.1f}")
    else:
        st.info("Dar neturite nei vieno įgūdžių vertinimo. Sukurkite pirmą!")

# === MAIN EXECUTION ===

def main():
    # Inicializuoti duomenų bazę
    init_database()
    
    # Tikrinti ar vartotojas prisijungęs
    if 'user' not in st.session_state:
        st.title("🎯 Įgūdžių Radar")
        st.write("Prisijunkite arba užsiregistruokite, kad galėtumėte išsaugoti savo įgūdžių profilius!")
        
        tab1, tab2 = st.tabs(["🔐 Prisijungimas", "📝 Registracija"])
        
        with tab1:
            login_form()
        
        with tab2:
            register_form()
    else:
        main_app()

if __name__ == "__main__":
    main()
