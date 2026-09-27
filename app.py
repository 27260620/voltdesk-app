import os
import sqlite3
import json
import pandas as pd
import requests
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="VoltDesk - Diagnóstico", page_icon="⚡️", layout="centered")

TOKEN_TELEGRAM = "8972769309:AAG5Gf58EORFvPJ2J050onWJXSBKdyv-pPM"
CHAT_ID_TELEGRAM = "8690664380"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_FILE = os.path.join(BASE_DIR, "chamados.db")

# Tenta criar a pasta no servidor e mostra na tela
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    st.sidebar.success(f"📁 Pasta 'uploads' OK em:\n{UPLOAD_DIR}")
except Exception as e:
    st.sidebar.error(f"❌ Erro ao criar pasta: {e}")

st.title("⚡️ Teste de Upload e Telegram ⚡️")

with st.form("form_teste"):
    nome = st.text_input("Seu Nome", value="Teste Hércules")
    descricao = st.text_input("Descrição", value="Teste de foto")
    foto = st.file_uploader("Selecione uma Imagem", type=["jpg", "png", "jpeg"])
    submit = st.form_submit_button("🚀 Testar Envio")

if submit:
    st.subheader("📋 Relatório do Diagnóstico:")
    
    if foto is None:
        st.warning("Selecione uma imagem para testar.")
    else:
        # 1. Teste do salvamento local
        caminho_salvo = None
        try:
            extensao = os.path.splitext(foto.name)[1].lower()
            nome_unico = f"teste_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extensao}"
            caminho_salvo = os.path.join(UPLOAD_DIR, nome_unico)
            
            with open(caminho_salvo, "wb") as f:
                f.write(foto.getbuffer())
                
            st.write("1️⃣ **Salvamento no Servidor:** ✅ Sucesso!")
            st.write(f"└─ Ficheiro guardado em: `{caminho_salvo}`")
            st.image(caminho_salvo, width=200)
        except Exception as e:
            st.error(f"1️⃣ **Salvamento no Servidor:** ❌ Falhou! Erro: {e}")

        # 2. Teste do envio para o Telegram
        if caminho_salvo and os.path.isfile(caminho_salvo):
            st.write("2️⃣ **Enviando para o Telegram...**")
            url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendPhoto"
            
            try:
                with open(caminho_salvo, "rb") as photo_file:
                    res = requests.post(
                        url,
                        data={"chat_id": CHAT_ID_TELEGRAM, "caption": "📸 Teste de imagem do VoltDesk"},
                        files={"photo": photo_file},
                        timeout=30
                    )
                
                if res.status_code == 200:
                    st.success("2️⃣ **Envio para Telegram:** ✅ Enviado com sucesso!")
                else:
                    st.error(f"2️⃣ **Envio para Telegram:** ❌ Erro da API Telegram (Código {res.status_code})")
                    st.code(res.text)
            except Exception as e:
                st.error(f"2️⃣ **Envio para Telegram:** ❌ Exceção na requisição: {e}")
