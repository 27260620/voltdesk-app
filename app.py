import streamlit as st
import sqlite3
import pandas as pd
import requests
import os

# Configuração da página
st.set_page_config(page_title="VoltDesk - Chamados", page_icon="⚡", layout="centered")

# CSS Customizado: Oculta o indicador de execução e ajusta o visual
st.markdown("""
    <style>
    div[data-testid="stStatusWidget"] {
        visibility: hidden;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

DB_FILE = "chamados.db"
UPLOADS_DIR = "uploads"

# Garante que a pasta de uploads existe na nuvem
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR, exist_ok=True)

# Função para inicializar o banco de dados
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS chamados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            apto TEXT NOT NULL,
            whatsapp TEXT NOT NULL,
            servico TEXT NOT NULL,
            descricao TEXT NOT NULL,
            dia_pref TEXT,
            turno_pref TEXT,
            foto TEXT,
            status TEXT DEFAULT '⚫ Pendente',
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Telegram Bot Credentials (ajuste se necessário)
TOKEN_TELEGRAM = "8972769309:AAG5Gf58EORFvPJ2J050onWJXSBKdyv-pPM"
CHAT_ID_TELEGRAM = "8690664380"

def enviar_notificacao_telegram(nome, apto, servico, descricao):
    if not TELEGRAM_TOKEN or "your_token" in TELEGRAM_TOKEN:
        return
    mensagem = f"🚨 *NOVO CHAMADO - VOLTDESK*\n\n👤 *Morador:* {nome}\n🏢 *Apto/Bloco:* {apto}\n🛠️ *Serviço:* {servico}\n📝 *Descrição:* {descricao}"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}, timeout=30)
    except Exception as e:
        print(f"Erro ao enviar notificação: {e}")

st.title("⚡ VoltDesk - Serviços")

menu = st.sidebar.radio("Navegação", ["Novo Chamado", "Área Administrativa"])

if menu == "Novo Chamado":
    st.subheader("Abertura de Chamado")
    
    with st.form("form_chamado", clear_on_submit=True):
        nome = st.text_input("Seu Nome *")
        apto = st.text_input("Apartamento / Bloco *")
        whatsapp = st.text_input("WhatsApp para Contato *")
        servico = st.selectbox("Tipo de Serviço *", ["Elétrica (Tomadas, Chuveiro, Luminárias, Disjuntores)", "Hidráulica", "Pintura / Reparos", "Outros"])
        descricao = st.text_area("Descrição do Problema *", placeholder="Explique o que precisa de ser feito...")
        
        foto_upload = st.file_uploader("Anexar Foto ou Vídeo (Opcional)", type=["jpg", "jpeg", "png", "mp4"])
        
        dia_pref = st.selectbox("Dia Preferencial", ["Qualquer dia", "Segunda a Sexta", "Sábado", "Domingo"])
        turno_pref = st.selectbox("Turno Preferencial", ["Qualquer turno", "Manhã", "Tarde", "Noite"])
        
        submitted = st.form_submit_button("🚀 Enviar Solicitação")
        
        if submitted:
            if not nome or not apto or not whatsapp or not descricao:
                st.error("Por favor, preencha todos os campos obrigatórios (*).")
            else:
                caminho_foto = None
                if foto_upload is not None:
                    try:
                        caminho_foto = os.path.join(UPLOADS_DIR, foto_upload.name)
                        with open(caminho_foto, "wb") as f:
                            f.write(foto_upload.getbuffer())
                    except Exception as e:
                        st.warning(f"Aviso: Não foi possível guardar o anexo, mas o chamado será registado.")
                        caminho_foto = None

                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''
                    INSERT INTO chamados (nome, apto, whatsapp, servico, descricao, dia_pref, turno_pref, foto)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (nome, apto, whatsapp, servico, descricao, dia_pref, turno_pref, caminho_foto))
                conn.commit()
                conn.close()
                
                enviar_notificacao_telegram(nome, apto, servico, descricao)
                st.success("✅ Solicitação enviada com sucesso! Em breve entrarei em contato via WhatsApp.")

elif menu == "Área Administrativa":
    st.subheader("Painel Administrativo")
    senha = st.text_input("Senha de Acesso", type="password")
    
    if senha == "1234":
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM chamados ORDER BY id DESC", conn)
        conn.close()
        
        if df.empty:
            st.info("Nenhum chamado registado até o momento.")
        else:
            for index, row in df.iterrows():
                with st.expander(f"{row['status']} - {row['servico']} ({row['nome']} - Apto {row['apto']})"):
                    st.write(f"**Morador:** {row['nome']}")
                    st.write(f"**Apto:** {row['apto']}")
                    st.write(f"**WhatsApp:** {row['whatsapp']}")
                    st.write(f"**Descrição:** {row['descricao']}")
                    st.write(f"**Preferência:** {row['dia_pref']} - {row['turno_pref']}")
                    
                    if row['foto'] and os.path.exists(str(row['foto'])):
                        if str(row['foto']).lower().endswith(('.png', '.jpg', '.jpeg')):
                            st.image(row['foto'], width=300)
                        elif str(row['foto']).lower().endswith('.mp4'):
                            st.video(row['foto'])
                    
                    novo_status = st.selectbox(
                        "Alterar Status",
                        ["⚫ Pendente", "🔵 Em Orçamento", "🟡 Agendado", "🟢 Concluído", "🔴 Cancelado"],
                        index=["⚫ Pendente", "🔵 Em Orçamento", "🟡 Agendado", "🟢 Concluído", "🔴 Cancelado"].index(row['status']) if row['status'] in ["⚫ Pendente", "🔵 Em Orçamento", "🟡 Agendado", "🟢 Concluído", "🔴 Cancelado"] else 0,
                        key=f"status_{row['id']}"
                    )
                    
                    if st.button("Atualizar Status", key=f"btn_{row['id']}"):
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("UPDATE chamados SET status = ? WHERE id = ?", (novo_status, row['id']))
                        conn.commit()
                        conn.close()
                        st.success("Status atualizado!")
                        st.rerun()
