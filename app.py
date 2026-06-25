import streamlit as st
import json
import os
import pandas as pd
from core_engine import process_statement_with_gemini
from processor import build_accounting_dataframe

st.set_page_config(page_title="Conciliação Contábil", layout="wide")

# =====================================================================
# PLANO DE CONTAS EDITÁVEL (Substitui o Ensinamento da IA)
# =====================================================================
DEFAULT_PLANO = [
    {"termo": "Light, luz", "conta": "513119"},
    {"termo": "Cedae, água, esgoto", "conta": "513120"},
    {"termo": "Telefone, claro, vivo, oi, tim", "conta": "513121"},
    {"termo": "Seguros", "conta": "513123"},
    {"termo": "GC, contabilidade", "conta": "513124"},
    {"termo": "IOF", "conta": "515101"},
    {"termo": "IPTU", "conta": "515102"},
    {"termo": "DARF", "conta": "211813"},
    {"termo": "Salário", "conta": "211101"},
    {"termo": "Empréstimo, Capital de giro", "conta": "211405"},
    {"termo": "Rend., aplic, apl, rendimento, auto mais", "conta": "111399"},
    {"termo": "Lis", "conta": "514102"}
]

def carregar_plano_contas():
    if not os.path.exists("data"):
        os.makedirs("data")
    caminho = "data/plano_contas_simplificado.json"
    
    # Se não existir, cria um novo com os dados padrão exigidos
    if not os.path.exists(caminho):
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump({"contas": DEFAULT_PLANO}, f, indent=4, ensure_ascii=False)
        return pd.DataFrame(DEFAULT_PLANO)
    
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            data = json.load(f)
            return pd.DataFrame(data.get("contas", []))
    except:
        return pd.DataFrame(DEFAULT_PLANO)

st.markdown("## Plano de Contas Simplificado")
with st.expander("Editar Plano de Contas", expanded=False):
    st.info("**Regras fixas:** Entradas não listadas vão para **112201** e saídas não listadas vão para **516199**.")
    
    df_plano = carregar_plano_contas()
    
    edited_df = st.data_editor(
        df_plano, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "termo": st.column_config.TextColumn("Palavra-chave no Extrato", help="O que a IA deve buscar no histórico"),
            "conta": st.column_config.TextColumn("Código da Conta")
        }
    )
    
    if st.button("💾 Salvar Plano de Contas"):
        plano_dict = {"contas": edited_df.to_dict(orient="records")}
        with open("data/plano_contas_simplificado.json", "w", encoding="utf-8") as f:
            json.dump(plano_dict, f, indent=4, ensure_ascii=False)
        st.success("Plano atualizado com sucesso!")

st.markdown("---")
# =====================================================================

st.markdown("## Conciliação Bancária Automática - GC Contábil")

csv_delimiter = st.selectbox("Delimitador do CSV:", ["; (Padrão Brasil)", ", (Internacional)"])
uploaded_file = st.file_uploader("Faça o Upload do Extrato (PDF):", type=["pdf"])

def formatar_brl(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

if uploaded_file and st.button("Processar Extrato"):
    with st.spinner("Classificando e gerando lançamentos..."):
        
        plano_txt = edited_df.to_string(index=False)
        result = process_statement_with_gemini(uploaded_file.read(), uploaded_file.type, plano_txt)
        
        if result and "transactions" in result:
            df = build_accounting_dataframe(result["transactions"])
            
            # Ordenação por data
            df['DATA_DT'] = pd.to_datetime(df['DATA'], dayfirst=True)
            df = df.sort_values('DATA_DT')
            
            # Nova Numeração: Sequencial direta (1, 2, 3...)
            df['N LANÇAMENTO'] = range(1, len(df) + 1)
            
            # Métricas formatadas no padrão brasileiro
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Saldo Inicial", f"R$ {formatar_brl(result.get('saldo_inicial', 0))}")
            c2.metric("Saldo Final", f"R$ {formatar_brl(result.get('saldo_final', 0))}")
            c3.metric("Total Entradas", f"R$ {formatar_brl(result.get('total_entradas', 0))}")
            c4.metric("Total Saídas", f"R$ {formatar_brl(result.get('total_saidas', 0))}")
            
            colunas_ordenadas = [
                "DEBITO", "CREDITO", "DATA", "VALOR", 
                "HISTORICO", "N LANÇAMENTO"
            ]
            
            df_final = df[colunas_ordenadas]
            
            st.dataframe(df_final, use_container_width=True)
            
            # Salvando o CSV com delimitador correto
            sep = ";" if ";" in csv_delimiter else ","
            csv = df_final.to_csv(index=False, sep=sep, encoding='utf-8-sig')
            st.download_button("Baixar Planilha", csv, "conciliacao.csv", "text/csv")