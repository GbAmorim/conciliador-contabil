import os
import io
import json
import streamlit as st
from google import genai
from google.genai import types

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = None

def get_gemini_client():
    if not API_KEY:
        return None
    return genai.Client(api_key=API_KEY)

def process_statement_with_gemini(pdf_bytes, file_mime, plano_contas_txt):
    client = get_gemini_client()
    if not client:
        st.error("Chave de API não localizada.")
        return None

    try:
        temp_file = client.files.upload(
            file=io.BytesIO(pdf_bytes),
            config=types.UploadFileConfig(mime_type=file_mime)
        )

        transaction_schema = {
            "type": "OBJECT",
            "properties": {
                "saldo_inicial": {"type": "NUMBER"},
                "saldo_final": {"type": "NUMBER"},
                "total_entradas": {"type": "NUMBER"},
                "total_saidas": {"type": "NUMBER"},
                "transactions": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "data": {"type": "STRING"},
                            "historico": {"type": "STRING"},
                            "valor": {"type": "NUMBER"},
                            "tipo": {"type": "STRING", "enum": ["ENTRADA", "SAIDA"]},
                            "conta_classificada": {"type": "STRING"}
                        },
                        "required": ["data", "historico", "valor", "tipo", "conta_classificada"]
                    }
                }
            },
            "required": ["transactions", "saldo_inicial", "saldo_final", "total_entradas", "total_saidas"]
        }

        prompt = f"""
        Você é um especialista em contabilidade. Analise o extrato e retorne um JSON com as transações.
        
        Instruções:
        1. Extraia o saldo inicial, final, total de entradas e total de saídas.
        2. Para as transações, ignore resumos e extraia cada item real.
        
        --- PLANO DE CONTAS CUSTOMIZÁVEL ---
        Classifique OBRIGATORIAMENTE usando os códigos abaixo caso o histórico da transação contenha a palavra-chave correspondente:
        {plano_contas_txt}
        
        --- REGRAS DE EXCEÇÃO (FALLBACK OBRIGATÓRIO) ---
        Se o item não contiver NENHUMA das palavras-chave da lista acima, siga RIGOROSAMENTE esta regra:
        - Se for uma SAÍDA (Despesa), classifique na conta: 516199
        - Se for uma ENTRADA (Receita), classifique na conta: 112201
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[temp_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=transaction_schema,
                temperature=0.1
            )
        )

        client.files.delete(name=temp_file.name)
        return json.loads(response.text)

    except Exception as e:
        st.error(f"Erro crítico: {e}")
        return None