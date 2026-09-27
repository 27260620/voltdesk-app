import os
import sqlite3
import pandas as pd
import requests
import streamlit as st
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÕES INICIAIS & CREDENCIAIS
# ==============================================================================
st.set_page_config(page_title="VoltDesk", page_icon="⚡️", layout="centered")

TOKEN_TELEGRAM = "8972769309:AAG5Gf58EORFvPJ2J050onWJXSBKdyv-pPM"
CHAT_ID_TELEGRAM = "8690664380"

UPLOAD_DIR = "uploads"
DB_FILE = "chamados.db"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ==============================================================================
# DICIONÁRIO DO FAROL DE CORES POR STATUS
# ==============================================================================
FAROL_STATUS = {
    "Pendente": "⚫",
    "Em Orçamento": "🔵",
    "Agendado": "🟡",
    "Concluído": "🟢",
    "Cancelado": "🔴"
}

# ==============================================================================
# BANCO DE DADOS (SQLITE)
# ==============================================================================
def get_db():
    return sqlite3.connect(DB_FILE)

@st.cache_resource
def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chamados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                bloco_apto TEXT NOT NULL,
                whatsapp TEXT NOT NULL,
                categoria TEXT NOT NULL,
                descricao TEXT NOT NULL,
                caminho_foto TEXT,
                data_preferencial TEXT,
                turno_preferencial TEXT,
                status TEXT DEFAULT 'Pendente' CHECK (status IN ('Pendente', 'Em Orçamento', 'Agendado', 'Concluído', 'Cancelado')),
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

init_db()

# ==============================================================================
# FUNÇÃO DE NOTIFICAÇÃO EM TEMPO REAL (TELEGRAM)
# ==============================================================================
def enviar_notificacao(nome, bloco_apto, whatsapp, categoria, descricao, dia, turno, id_chamado, caminho_foto=None):
    if TOKEN_TELEGRAM == "SEU_TOKEN_DO_BOTFATHER_AQUI":
        st.info("ℹ️ Para receber alertas no Telegram, preencha o TOKEN e CHAT_ID no código.")
        return

    num_limpo = "".join(filter(str.isdigit, whatsapp))
    if not num_limpo.startswith("55"):
        num_limpo = f"55{num_limpo}"
    
    link_wa = f"https://wa.me/{num_limpo}?text=Ol%C3%A1%20{nome}%2C%20recebi%20seu%20chamado%20%23{id_chamado}%20de%20{categoria}.%20Podemos%20agendar%3F"

    mensagem = f"""
⚡️ <b>NOVO CHAMADO NO CONDOMÍNIO!</b> ⚡️

 <b>ID:</b> #{id_chamado}
 <b>Morador:</b> {nome}
 <b>Local:</b> {bloco_apto}
 <b>Serviço:</b> {categoria}
 <b>Agendamento:</b> {dia} ({turno})

 <b>Descrição:</b>
<i>{descricao}</i>
    """

    payload = {
        "chat_id": CHAT_ID_TELEGRAM,
        "caption": mensagem,
        "text": mensagem,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[{"text": "💬 Abrir conversa no WhatsApp", "url": link_wa}]]
        }
    }

    try:
        if caminho_foto and isinstance(caminho_foto, str) and os.path.exists(caminho_foto) and caminho_foto.lower().endswith(('.jpg', '.png', '.jpeg')):
            url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendPhoto"
            with open(caminho_foto, "rb") as photo_file:
                # Timeout aumentado para 30s para fotos pesadas não darem estouro de tempo
                requests.post(url, data={"chat_id": CHAT_ID_TELEGRAM, "caption": mensagem, "parse_mode": "HTML", "reply_markup": payload["reply_markup"]}, files={"photo": photo_file}, timeout=30)
        else:
            url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
            requests.post(url, json=payload, timeout=15)
    except Exception as e:
        # Fallback: Tenta enviar pelo menos a mensagem de texto sem a imagem caso ocorra timeout
        try:
            url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
            payload_txt = payload.copy()
            payload_txt["text"] = mensagem + "\n\n⚠️ <i>(Anexo não enviado por lentidão na conexão)</i>"
            requests.post(url, json=payload_txt, timeout=10)
        except:
            pass
        st.warning(f"Chamado salvo! Houve um aviso no Telegram: {e}")

# ==============================================================================
# INTERFACE STREAMLIT
# ==============================================================================
aba = st.sidebar.radio("Navegação", ["Abrir Chamado ", "Painel Admin (Gestão)"])

# ------------------------------------------------------------------------------
# ABA 1: FORMULÁRIO DO VIZINHO
# ------------------------------------------------------------------------------
if aba == "Abrir Chamado ":
    st.title("⚡️VoltDesk⚡️")
    st.markdown("Atendimento residencial para pequenos reparos elétricos, hidráulicos e outros serviços.")

    with st.form("form_chamado", clear_on_submit=True):
        nome = st.text_input("Seu Nome*", placeholder="Ex: João Paulo")
        bloco_apto = st.text_input("Bloco / Apartamento*", placeholder="Ex: Bloco B - Apto 204")
        whatsapp = st.text_input("WhatsApp para Contato*", placeholder="Ex: 84 99999-9999")
        
        categoria = st.selectbox(
            "Tipo de Serviço*",
            [
                "Elétrica (Tomadas, Chuveiro, Luminárias, Disjuntores)",
                "Pequenos Reparos (Suporte TV, Cortinas, Montagens)",
                "Hidráulica Leve (Reparo de Torneira, Vazamentos simples)",
                "Outros"
            ]
        )
        
        descricao = st.text_area("Descrição do Problema*", placeholder="Explique o que precisa ser feito...")
        foto = st.file_uploader("Anexar Foto ou Vídeo (Opcional)", type=["jpg", "png", "jpeg", "mp4"])
        
        col1, col2 = st.columns(2)
        with col1:
            data_pref = st.selectbox("Dia Preferencial", ["Sábado", "Domingo"])
        with col2:
            turno_pref = st.selectbox("Turno Preferencial", ["Manhã", "Tarde"])
            
        submit = st.form_submit_button("🚀 Enviar Solicitação")

    if submit:
        if not nome or not bloco_apto or not whatsapp or not descricao:
            st.error("Preencha todos os campos obrigatórios com asterisco (*).")
        else:
            caminho_salvo = None
            if foto is not None:
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{foto.name}"
                caminho_salvo = os.path.join(UPLOAD_DIR, filename)
                with open(caminho_salvo, "wb") as f:
                    f.write(foto.getbuffer())

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO chamados 
                    (nome, bloco_apto, whatsapp, categoria, descricao, caminho_foto, data_preferencial, turno_preferencial)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (nome, bloco_apto, whatsapp, categoria, descricao, caminho_salvo, data_pref, turno_pref))
                conn.commit()
                id_gerado = cursor.lastrowid

            enviar_notificacao(
                nome=nome,
                bloco_apto=bloco_apto,
                whatsapp=whatsapp,
                categoria=categoria,
                descricao=descricao,
                dia=data_pref,
                turno=turno_pref,
                id_chamado=id_gerado,
                caminho_foto=caminho_salvo
            )

            st.success("✅ Solicitação enviada com sucesso! Em breve entrarei em contato via WhatsApp.")

# ------------------------------------------------------------------------------
# ABA 2: PAINEL DE GESTÃO DO ELETRICISTA
# ------------------------------------------------------------------------------
elif aba == "Painel Admin (Gestão)":
    st.title("📋 Gestão de Chamados")
    senha = st.sidebar.text_input("Senha de Acesso", type="password")
    
    if senha == "1234":  # Altere para a senha que desejar
        with get_db() as conn:
            df = pd.read_sql_query("SELECT * FROM chamados ORDER BY id DESC", conn)

        if df.empty:
            st.info("Nenhum chamado registrado até o momento.")
        else:
            st.metric("Total de Chamados", len(df))
            st.divider()

            # Controle de Alteração de Status
            lista_ids = df['id'].tolist()
            col_id, col_st, col_bt = st.columns([1, 2, 1])
            
            with col_id:
                ch_id = st.selectbox("ID do Chamado", options=lista_ids)
            
            # Pega o status atual do ID selecionado para preencher o selectbox automaticamente
            status_atual = df.loc[df['id'] == ch_id, 'status'].values[0]
            opcoes_status = ["Pendente", "Em Orçamento", "Agendado", "Concluído", "Cancelado"]
            index_atual = opcoes_status.index(status_atual) if status_atual in opcoes_status else 0

            with col_st:
                st_novo = st.selectbox("Novo Status", opcoes_status, index=index_atual)
            
            with col_bt:
                st.write("")
                if st.button("Atualizar"):
                    with get_db() as conn:
                        conn.execute("UPDATE chamados SET status = ? WHERE id = ?", (st_novo, ch_id))
                        conn.commit()
                    st.success(f"Status do Chamado #{ch_id} atualizado para {st_novo}!")
                    st.rerun()

            st.subheader("Lista de Solicitações")
            for _, row in df.iterrows():
                # Define a bolinha de cor do farol conforme o status
                emoji_farol = FAROL_STATUS.get(row['status'], "⚫")
                
                with st.expander(f"{emoji_farol} ID #{row['id']} - {row['nome']} ({row['bloco_apto']}) - {row['status']}"):
                    st.write(f"**WhatsApp:** {row['whatsapp']}")
                    st.write(f"**Categoria:** {row['categoria']}")
                    st.write(f"**Descrição:** {row['descricao']}")
                    st.write(f"**Data/Turno:** {row['data_preferencial']} - {row['turno_preferencial']}")
                    st.write(f"**Solicitado em:** {row['criado_em']}")
                    
                    caminho_foto = row['caminho_foto']
                    if pd.notna(caminho_foto) and str(caminho_foto).strip() != "":
                        caminho_str = str(caminho_foto)
                        if os.path.exists(caminho_str):
                            if caminho_str.lower().endswith(('.mp4', '.mov')):
                                st.video(caminho_str)
                            else:
                                st.image(caminho_str, width=300)
    else:
        st.warning("Digite a senha de administrador na barra lateral para acessar a lista de chamados.")