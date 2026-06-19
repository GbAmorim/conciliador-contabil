import os
import io
import json
import streamlit as st
from google import genai
from google.genai import types

# Busca a chave no arquivo secrets.toml
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
        # 1. Faz o upload do documento
        temp_file = client.files.upload(
            file=io.BytesIO(pdf_bytes),
            config=types.UploadFileConfig(mime_type=file_mime)
        )

        # 2. Definição do Schema (usando dicionário puro para evitar erros de sintaxe)
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

        # --- NOVA FUNCIONALIDADE: LEITURA DAS REGRAS ---
        regras_json_str = "Nenhuma regra específica configurada."
        if os.path.exists("data/regras.json"):
            try:
                with open("data/regras.json", "r", encoding="utf-8") as f:
                    regras_data = json.load(f)
                    if regras_data.get("regras"):
                        # Converte a lista de regras para um texto formatado
                        regras_json_str = json.dumps(regras_data["regras"], ensure_ascii=False, indent=2)
            except Exception:
                pass
        # -----------------------------------------------

        # 3. Prompt de extração
        prompt = f"""
        Você é um especialista em contabilidade. Analise o extrato e retorne um JSON com os saldos iniciais/finais, totais e a lista detalhada de transações.
        
        Instruções:
        1. Extraia o saldo inicial, final, total de entradas e total de saídas exatamente como aparecem no documento, não é necessário calcular nada, essas informações aparecem geralmente no início do documento.
        2. Para as transações, ignore resumos e extraia cada item real.
        3. Classifique cada item usando estritamente os códigos de 6 dígitos do plano de contas abaixo.
        
        --- REGRAS DE CLASSIFICAÇÃO PRIORITÁRIA ---
        Verifique se a descrição do item contém algum destes termos. Se contiver, USE OBRIGATORIAMENTE o código da conta correspondente abaixo:
        {regras_json_str}
        
        --- PLANO DE CONTAS ---
        {plano_contas_txt}
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',  # <--- VOLTE PARA ESTE MODELO
            contents=[temp_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=transaction_schema,
                temperature=0.1
            )
        )

        # 4. Limpeza
        client.files.delete(name=temp_file.name)

        return json.loads(response.text)

    except Exception as e:
        st.error(f"Erro crítico: {e}")
        return None