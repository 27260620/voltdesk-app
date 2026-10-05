import os
import sqlite3
import json
import io
import pandas as pd
import requests
import streamlit as st
from datetime import datetime
from PIL import Image

# ==============================================================================
# CONFIGURAÇÕES INICIAIS & CREDENCIAIS.
# ==============================================================================
st.set_page_config(page_title="VoltDesk", page_icon="⚡️", layout="centered")

TOKEN_TELEGRAM = "8972769309:AAG5Gf58EORFvPJ2J050onWJXSBKdyv-pPM"
CHAT_ID_TELEGRAM = "8690664380"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_FILE = os.path.join(BASE_DIR, "chamados.db")

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
# FUNÇÃO DE OTIMIZAÇÃO DE IMAGEM PARA DISPOSITIVOS MÓVEIS
# ==============================================================================
def otimizar_e_salvar_imagem(file_uploader_object, upload_dir):
    """
    Comprime fotos enviadas de celulares externos para evitar erro de memória/timeout.
    """
    try:
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        caminho_final = os.path.join(upload_dir, filename)

        # Se for vídeo, guarda diretamente
        if file_uploader_object.name.lower().endswith(('.mp4', '.mov')):
            caminho_video = os.path.join(upload_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_uploader_object.name}")
            with open(caminho_video, "wb") as f:
                f.write(file_uploader_object.getvalue())
            return caminho_video

        # Lê os bytes diretamente para evitar travamento de buffer no celular
        bytes_data = file_uploader_object.getvalue()
        image_stream = io.BytesIO(bytes_data)

        # Abre e converte a foto
        img = Image.open(image_stream)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Redimensiona mantendo a proporção (máximo 1280px) e salva comprimida
        img.thumbnail((1280, 1280))
        img.save(caminho_final, "JPEG", quality=75, optimize=True)
        
        return caminho_final
    except Exception as e:
        st.error(f"Erro ao processar imagem: {e}")
        return None

# ==============================================================================
# FUNÇÃO DE NOTIFICAÇÃO EM TEMPO REAL (TELEGRAM)
# ==============================================================================
def enviar_notificacao(nome, bloco_apto, whatsapp, categoria, descricao, dia, turno, id_chamado, caminho_foto=None):
    if not TOKEN_TELEGRAM or TOKEN_TELEGRAM == "SEU_TOKEN_DO_BOTFATHER_AQUI":
        return

    num_limpo = "".join(filter(str.isdigit, whatsapp))
    if not num_limpo.startswith("55"):
        num_limpo = f"55{num_limpo}"
    
    link_wa = f"https://wa.me/{num_limpo}?text=Ol%C3%A1%20{nome}%2C%20recebi%20seu%20chamado%20%23{id_chamado}%20de%20{categoria}.%20Podemos%20agendar%3F"

    mensagem = f"""⚡️ <b>NOVO CHAMADO NO CONDOMÍNIO!</b> ⚡️

<b>ID:</b> #{id_chamado}
<b>Morador:</b> {nome}
<b>Local:</b> {bloco_apto}
<b>Serviço:</b> {categoria}
<b>Agendamento:</b> {dia} ({turno})

<b>Descrição:</b>
<i>{descricao}</i>
"""

    inline_keyboard = {"inline_keyboard": [[{"text": "💬 Abrir conversa no WhatsApp", "url": link_wa}]]}
    reply_markup_json = json.dumps(inline_keyboard)

    sucesso_envio = False

    if caminho_foto and isinstance(caminho_foto, str) and os.path.isfile(caminho_foto):
        ext = caminho_foto.lower()
        if ext.endswith(('.jpg', '.png', '.jpeg')):
            try:
                url_photo = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendPhoto"
                with open(caminho_foto, "rb") as photo_file:
                    payload_data = {
                        "chat_id": CHAT_ID_TELEGRAM,
                        "caption": mensagem,
                        "parse_mode": "HTML",
                        "reply_markup": reply_markup_json
                    }
                    res = requests.post(
                        url_photo,
                        data=payload_data,
                        files={"photo": photo_file},
                        timeout=45
                    )
                    if res.status_code == 200:
                        sucesso_envio = True
            except Exception:
                sucesso_envio = False

    if not sucesso_envio:
        try:
            url_msg = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
            payload_msg = {
                "chat_id": CHAT_ID_TELEGRAM,
                "text": mensagem,
                "parse_mode": "HTML",
                "reply_markup": inline_keyboard
            }
            requests.post(url_msg, json=payload_msg, timeout=15)
        except Exception as e:
            st.warning(f"Chamado salvo, mas ocorreu um erro no alerta do Telegram: {e}")

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
        foto = st.file_uploader("Anexar Foto ou Vídeo (Opcional)", type=["jpg", "png", "jpeg", "webp", "mp4"])
        
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
                caminho_salvo = otimizar_e_salvar_imagem(foto, UPLOAD_DIR)

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
    
    if senha == "1234":
        with get_db() as conn:
            df = pd.read_sql_query("SELECT * FROM chamados ORDER BY id DESC", conn)

        if df.empty:
            st.info("Nenhum chamado registrado até o momento.")
        else:
            st.metric("Total de Chamados", len(df))
            st.divider()

            lista_ids = df['id'].tolist()
            col_id, col_st, col_bt = st.columns([1, 2, 1])
            
            with col_id:
                ch_id = st.selectbox("ID do Chamado", options=lista_ids)
            
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
