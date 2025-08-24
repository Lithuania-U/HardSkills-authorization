import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import json
import hashlib
import sqlite3
from datetime import datetime
import io
import base64

# === KONFIGŪRACIJA ===
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

# Saugoti angles session state
if 'angles' not in st.session_state:
    st.session_state.angles = angles

DB_PATH = "skills_users.db"

# === DUOMENŲ BAZĖS FUNKCIJOS ===
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
    """Užšifruoti slaptažodį"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hash_value):
    """Patikrinti slaptažodį"""
    return hash_password(password) == hash_value

def create_user(email, password, username):
    """Sukurti naują vartotoją"""
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
    """Autentifikuoti vartotoją"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, password_hash, username FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user and verify_password(password, user[1]):
        # Atnaujinti paskutinio prisijungimo laiką
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user[0],))
        conn.commit()
        conn.close()
        return {'id': user[0], 'username': user[2], 'email': email}
    return None

def save_skill_assessment(user_id, skills_data, comment=""):
    """Išsaugoti įgūdžių vertinimą"""
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
    """Gauti vartotojo įgūdžių vertinimus"""
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

# === CIRCULAR LOLLIPOP RADAR DIAGRAMA ===
def create_circular_lollipop_chart(skills_data, title="Jūsų įgūdžių profilis"):
    """Sukurti circular lollipop radar diagramą (kaip Python Graph Gallery)"""
    
    # Paruošti duomenis
    categories = []
    values = []
    colors = []
    
    for angle in sorted(skills_data.keys()):
        angle_int = int(angle) if isinstance(angle, str) else angle
        categories.append(angles.get(angle_int, f"Kampas {angle}"))
        values.append(skills_data[angle])
        
        # Spalvų gradientai pagal vertę
        if skills_data[angle] >= 8:
            colors.append('#2E8B57')  # Žalia - stiprus
        elif skills_data[angle] >= 6:
            colors.append('#FFD700')  # Geltona - vidutinis
        elif skills_data[angle] >= 4:
            colors.append('#FF8C00')  # Oranžinė - silpnas
        else:
            colors.append('#DC143C')  # Raudona - labai silpnas
    
    N = len(categories)
    
    # Apskaičiuoti kampus radianais
    theta = np.linspace(0.0, 2 * np.pi, N, endpoint=False)
    
    # Sukurti figūrą
    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(projection='polar'))
    
    # Nustatyti tamsų foną
    fig.patch.set_facecolor('#1e1e1e')
    ax.set_facecolor('#1e1e1e')
    
    # Piešti lollipop stulpelius
    bars = ax.bar(theta, values, width=0.15, bottom=0, alpha=0.8)
    
    # Nustatyti spalvas kiekvienam stulpeliui
    for bar, color in zip(bars, colors):
        bar.set_color(color)
        bar.set_edgecolor('white')
        bar.set_linewidth(1)
    
    # Pridėti "lollipop" taškus viršuje
    ax.scatter(theta, values, c=colors, s=100, alpha=1, zorder=3, edgecolors='white', linewidths=2)
    
    # Pridėti vertes ant taškų
    for angle, value, color in zip(theta, values, colors):
        ax.text(angle, value + 0.3, str(value), 
                ha='center', va='center', fontsize=10, 
                color='white', weight='bold', zorder=4)
    
    # Nustatyti ašių parametrus
    ax.set_ylim(0, 10)
    ax.set_theta_zero_location('N')  # Pradėti nuo viršaus
    ax.set_theta_direction(-1)  # Clockwise
    
    # Nustatyti kategorijų pavadinimus
    ax.set_xticks(theta)
    ax.set_xticklabels([cat[:25] + '...' if len(cat) > 25 else cat for cat in categories], 
                       fontsize=8, color='white')
    
    # Nustatyti radialias ašis
    ax.set_ylim(0, 10)
    ax.set_yticks(range(0, 11, 2))
    ax.set_yticklabels(range(0, 11, 2), fontsize=8, color='white')
    ax.grid(True, color='gray', alpha=0.3)
    
    # Pridėti pavadinimą
    plt.title(title, pad=30, fontsize=16, color='white', weight='bold')
    
    # Pridėti legendą
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2E8B57', label='Stiprus (8-10)'),
        Patch(facecolor='#FFD700', label='Vidutinis (6-7)'),
        Patch(facecolor='#FF8C00', label='Silpnas (4-5)'),
        Patch(facecolor='#DC143C', label='Labai silpnas (1-3)')
    ]
    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.3, 1.0), 
              facecolor='#1e1e1e', edgecolor='white', labelcolor='white')
    
    plt.tight_layout()
    return fig

def fig_to_base64(fig):
    """Konvertuoti matplotlib figūrą į base64 stringą"""
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight', 
                facecolor='#1e1e1e', edgecolor='none')
    img_buffer.seek(0)
    img_string = base64.b64encode(img_buffer.read()).decode()
    plt.close(fig)
    return img_string

# === AUTORIZACIJOS FORMOS ===
def login_form():
    """Prisijungimo forma"""
    st.subheader("🔐 Prisijungimas")
    with st.form("login_form"):
        email = st.text_input("El. paštas", placeholder="jusu.pastas@example.com")
        password = st.text_input("Slaptažodis", type="password", 
                                help="Jei pamiršote slaptažodį, susisiekite su administratoriumi")
        submit_button = st.form_submit_button("Prisijungti", type="primary")
        
        if submit_button:
            if email and password:
                user = authenticate_user(email, password)
                if user:
                    st.session_state.user = user
                    st.success(f"Sveiki sugrįžę, {user['username']}! 👋")
                    st.rerun()
                else:
                    st.error("❌ Neteisingas el. paštas arba slaptažodis!")
            else:
                st.error("❌ Prašome užpildyti visus laukus!")

def register_form():
    """Registracijos forma"""
    st.subheader("📝 Registracija")
    with st.form("register_form"):
        username = st.text_input("Vartotojo vardas", placeholder="JonasJonaitis")
        email = st.text_input("El. paštas", placeholder="jonas@example.com")
        
        # Slaptažodžio laukas su pasiūlymais
        password = st.text_input("Slaptažodis", type="password", 
                                help="💡 Naudokite bent 8 simbolius, skaičius ir specialius ženklus")
        password_confirm = st.text_input("Patvirtinkite slaptažodį", type="password")
        
        # Slaptažodžio stiprumo tikrinimas
        if password:
            strength_score = 0
            feedback = []
            
            if len(password) >= 8:
                strength_score += 1
            else:
                feedback.append("• Bent 8 simboliai")
            
            if any(c.isupper() for c in password):
                strength_score += 1
            else:
                feedback.append("• Didžioji raidė")
                
            if any(c.islower() for c in password):
                strength_score += 1
            else:
                feedback.append("• Mažoji raidė")
                
            if any(c.isdigit() for c in password):
                strength_score += 1
            else:
                feedback.append("• Skaičius")
                
            if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                strength_score += 1
            else:
                feedback.append("• Specialus ženklas (!@#$ etc.)")
            
            # Rodyti stiprumą
            if strength_score <= 2:
                st.error(f"🔴 Silpnas slaptažodis. Trūksta: {', '.join(feedback)}")
            elif strength_score <= 3:
                st.warning(f"🟡 Vidutinis slaptažodis. Patobulinkite: {', '.join(feedback)}")
            elif strength_score <= 4:
                st.info(f"🔵 Geras slaptažodis. Galite pridėti: {', '.join(feedback)}")
            else:
                st.success("🟢 Stiprus slaptažodis!")
        
        # Generatoriaus pasiūlymas
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.form_submit_button("🎲 Generuoti", help="Sugeneruoti saugų slaptažodį"):
                import random
                import string
                chars = string.ascii_letters + string.digits + "!@#$%^&*"
                generated = ''.join(random.choice(chars) for _ in range(12))
                st.info(f"Pasiūlymas: `{generated}`")
        
        submit_button = st.form_submit_button("Registruotis", type="primary")
        
        if submit_button:
            if username and email and password and password_confirm:
                if password != password_confirm:
                    st.error("❌ Slaptažodžiai nesutampa!")
                elif len(password) < 6:
                    st.error("❌ Slaptažodis turi būti bent 6 simbolių ilgio!")
                else:
                    user_id = create_user(email, password, username)
                    if user_id:
                        st.success("✅ Registracija sėkminga! Dabar galite prisijungti.")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Vartotojas su tokiu el. paštu jau egzistuoja!")
            else:
                st.error("❌ Prašome užpildyti visus laukus!")

# === PROFILIO FUNKCIJOS ===
def show_profile():
    """Rodyti vartotojo profilį"""
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("⬅️ Grįžti į vertinimą"):
            st.session_state.show_profile = False
            st.rerun()
    
    st.header(f"👤 {st.session_state.user['username']} profilis")
    
    # Vartotojo informacija
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write(f"**El. paštas:** {st.session_state.user['email']}")
        st.write(f"**Vartotojo ID:** {st.session_state.user['id']}")
    
    st.divider()
    
    # Įgūdžių istorija
    st.subheader("📊 Jūsų įgūdžių istorija")
    
    assessments = get_user_assessments(st.session_state.user['id'])
    
    if assessments:
        for i, assessment in enumerate(assessments):
            with st.expander(f"🎯 Vertinimas #{len(assessments)-i} - {assessment['created_at'][:16]}"):
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Circular lollipop diagrama
                    try:
                        fig = create_circular_lollipop_chart(
                            assessment['data'], 
                            f"Vertinimas #{len(assessments)-i}"
                        )
                        st.pyplot(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Klaida rodant diagramą: {e}")
                
                with col2:
                    if assessment['comment']:
                        st.write(f"**💭 Komentaras:**")
                        st.info(assessment['comment'])
                    
                    # Statistikos
                    try:
                        avg_score = sum(assessment['data'].values()) / len(assessment['data'])
                        max_skill = max(assessment['data'].items(), key=lambda x: x[1])
                        min_skill = min(assessment['data'].items(), key=lambda x: x[1])
                        
                        st.metric("📊 Vidutinis balas", f"{avg_score:.1f}")
                        
                        st.write("**🏆 Stipriausia sritis:**")
                        st.success(f"{angles[max_skill[0]]} ({max_skill[1]}/10)")
                        
                        st.write("**📈 Tobulintina sritis:**")
                        st.warning(f"{angles[min_skill[0]]} ({min_skill[1]}/10)")
                        
                    except Exception as e:
                        st.error(f"Klaida skaičiuojant statistikas: {e}")
                
                st.divider()
    else:
        st.info("🎯 Dar neturite nei vieno įgūdžių vertinimo. Sukurkite pirmą!")

# === PAGRINDINĖ APLIKACIJA ===
def main_app():
    """Pagrindinė aplikacija prisijungusiems vartotojams"""
    
    # Viršutinė juosta su vartotojo info
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.title("🎯 Įgūdžių Radar")
        st.write(f"Sveiki, **{st.session_state.user['username']}**! 👋")
    
    with col2:
        if st.button("👤 Profilis", type="secondary"):
            st.session_state.show_profile = True
            st.rerun()
        if st.button("🚪 Atsijungti", type="secondary"):
            if 'user' in st.session_state:
                del st.session_state.user
            if 'show_profile' in st.session_state:
                del st.session_state.show_profile
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
        st.write("*Slinkite per visas kategorijas ir įvertinkite save*")
        skills_data = {}
        
        for angle, skill_name in angles.items():
            skills_data[angle] = st.slider(
                skill_name,
                min_value=1,
                max_value=10,
                value=5,
                key=f"skill_{angle}",
                help=f"Įvertinkite save kategorijoje: {skill_name}"
            )
    
    # Pagrindinis turinys
    col1, col2 = st.columns([2.5, 1])
    
    with col1:
        # Rodyti circular lollipop diagramą
        if skills_data:
            try:
                fig = create_circular_lollipop_chart(skills_data)
                st.pyplot(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Klaida generuojant diagramą: {e}")
    
    with col2:
        st.subheader("📊 Statistikos")
        if skills_data:
            avg_score = sum(skills_data.values()) / len(skills_data)
            max_skill = max(skills_data.items(), key=lambda x: x[1])
            min_skill = min(skills_data.items(), key=lambda x: x[1])
            
            st.metric("📊 Vidutinis balas", f"{avg_score:.1f}")
            
            st.write("**🏆 Stipriausia sritis:**")
            st.success(f"{angles[max_skill[0]][:30]}... ({max_skill[1]}/10)")
            
            st.write("**📈 Tobulintina sritis:**")
            st.warning(f"{angles[min_skill[0]][:30]}... ({min_skill[1]}/10)")
            
            st.divider()
            
            st.subheader("💾 Išsaugoti vertinimą")
            comment = st.text_area("💭 Pridėti refleksiją (neprivaloma)", 
                                 placeholder="Kaip jaučiatės dėl šio vertinimo? Kokie planai tobulėjimui?")
            
            if st.button("💾 Išsaugoti", type="primary"):
                try:
                    assessment_id = save_skill_assessment(
                        st.session_state.user['id'],
                        skills_data,
                        comment
                    )
                    st.success(f"✅ Vertinimas išsaugotas! ID: {assessment_id}")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Klaida saugojant: {e}")
                
            st.divider()
            
            # Eksporto mygtukai
            st.subheader("📥 Eksportuoti")
            
            # JSON eksportas
            if st.button("📄 Atsisiųsti JSON", help="Atsisiųskite duomenis JSON formatu"):
                try:
                    json_data = {
                        "user": st.session_state.user['username'],
                        "timestamp": datetime.now().isoformat(),
                        "skills": skills_data,
                        "statistics": {
                            "average": round(avg_score, 2),
                            "strongest": {
                                "category": angles[max_skill[0]],
                                "score": max_skill[1]
                            },
                            "weakest": {
                                "category": angles[min_skill[0]],
                                "score": min_skill[1]
                            }
                        },
                        "comment": comment if 'comment' in locals() else ""
                    }
                    json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="💾 Atsisiųsti JSON failą",
                        data=json_str,
                        file_name=f"skills_{st.session_state.user['username']}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                        mime="application/json"
                    )
                except Exception as e:
                    st.error(f"❌ Klaida eksportuojant: {e}")

# === MAIN EXECUTION ===
def main():
    """Pagrindinė funkcija"""
    # Inicializuoti duomenų bazę
    try:
        init_database()
    except Exception as e:
        st.error(f"❌ Klaida inicializuojant duomenų bazę: {e}")
        return
    
    # Tikrinti ar vartotojas prisijungęs
    if 'user' not in st.session_state:
        st.title("🎯 Įgūdžių Radar")
        st.markdown("""
        **Atraskite ir sekite savo įgūdžių augimą!**
        
        Šis įrankis padės jums:
        - 📊 Vizualizuoti savo įgūdžių profilį
        - 📈 Sekti progresą laike  
        - 🎯 Identifikuoti tobulintinas sritis
        - 💾 Išsaugoti savo vertinimus
        """)
        
        tab1, tab2 = st.tabs(["🔐 Prisijungimas", "📝 Registracija"])
        
        with tab1:
            login_form()
        
        with tab2:
            register_form()
    else:
        main_app()

if __name__ == "__main__":
    main()
