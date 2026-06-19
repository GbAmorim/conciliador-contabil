import streamlit as st
import json
import os
import pandas as pd
from core_engine import process_statement_with_gemini
from processor import build_accounting_dataframe

st.set_page_config(page_title="Conciliação Contábil", layout="wide")

# =====================================================================
# NOVA FUNCIONALIDADE: ENSINAMENTO DA IA (Regras Customizadas)
# =====================================================================
def carregar_regras():
    if not os.path.exists("data"):
        os.makedirs("data")
    caminho = "data/regras.json"
    if not os.path.exists(caminho):
        return pd.DataFrame(columns=["termo", "conta"])
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            data = json.load(f)
            return pd.DataFrame(data.get("regras", []))
    except:
        return pd.DataFrame(columns=["termo", "conta"])

st.markdown("## Ensinamento da IA")
with st.expander("Configurar Regras de Classificação Específicas", expanded=False):
    st.write("Adicione termos para guiar a IA. Para excluir, selecione a linha (clicando no quadrado vazio à esquerda) e aperte **Delete**.")
    
    df_regras = carregar_regras()
    
    edited_df = st.data_editor(
        df_regras, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "termo": st.column_config.TextColumn("Termo no Extrato", help="Ex: 'PIX SAMPAIO'"),
            "conta": st.column_config.TextColumn("Código da Conta", help="Ex: '11201'")
        }
    )
    
    if st.button(" Salvar Regras"):
        regras_dict = {"regras": edited_df.to_dict(orient="records")}
        with open("data/regras.json", "w", encoding="utf-8") as f:
            json.dump(regras_dict, f, indent=4, ensure_ascii=False)
        st.success("Regras atualizadas com sucesso!")

st.markdown("---")
# =====================================================================

st.markdown("## Conciliação Bancária Automática")

caminho_arquivo = os.path.join("data", "accounts.json")
with open(caminho_arquivo, "r", encoding="utf-8") as f:
    plano_contas_data = json.load(f)

conta_banco_reduzida = st.text_input("Código Reduzido do Banco:", value="111201")
csv_delimiter = st.selectbox("Delimitador:", ["; (Excel BR)", ", (Internacional)"])
uploaded_file = st.file_uploader("Upload PDF:", type=["pdf"])

if uploaded_file and st.button("Processar"):
    with st.spinner("Classificando..."):
        contexto = json.dumps(plano_contas_data)
        result = process_statement_with_gemini(uploaded_file.read(), uploaded_file.type, contexto)
        
        if result and "transactions" in result:
            df = build_accounting_dataframe(result["transactions"], conta_banco_reduzida)
            
            # Numeração por dia
            df['DATA_DT'] = pd.to_datetime(df['DATA'], dayfirst=True)
            df = df.sort_values('DATA_DT')
            df['Nº LANÇAMENTO'] = df.groupby('DATA_DT').ngroup() + 1
            
            # --- Exibição das 4 Métricas (Mantidas) ---
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Saldo Inicial", f"R$ {result.get('saldo_inicial', 0):,.2f}")
            c2.metric("Saldo Final", f"R$ {result.get('saldo_final', 0):,.2f}")
            c3.metric("Total Entradas", f"R$ {result.get('total_entradas', 0):,.2f}")
            c4.metric("Total Saídas", f"R$ {result.get('total_saidas', 0):,.2f}")
            
            # --- Ordem das colunas solicitada ---
            colunas_ordenadas = [
                "DÉBITO", "CRÉDITO", "DATA", "VALOR", 
                "HISTÓRICO DÉBITO", "HISTÓRICO CRÉDITO", "Nº LANÇAMENTO"
            ]
            
            # Garantir que todas as colunas existam antes de filtrar
            df_final = df[colunas_ordenadas]
            
            st.dataframe(df_final, use_container_width=True)
            
            sep = ";" if ";" in csv_delimiter else ","
            csv = df_final.to_csv(index=False, sep=sep, encoding='utf-8-sig')
            st.download_button(" Baixar CSV", csv, "conciliacao.csv", "text/csv")