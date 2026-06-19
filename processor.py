import pandas as pd

def build_accounting_dataframe(raw_transactions, conta_banco_reduzida):
    csv_rows = []
    
    for tx in raw_transactions:
        tipo = tx.get("tipo") 
        valor = float(tx.get("valor", 0))
        conta_contrapartida = tx.get("conta_classificada")
        historico_orig = str(tx.get("historico")).upper().strip()
        
        if tipo == "SAIDA":
            debito, credito = conta_contrapartida, ""
            hist_debito, hist_credito = historico_orig, ""
        else: # ENTRADA
            debito, credito = "", conta_contrapartida
            hist_debito, hist_credito = "", historico_orig
            
        csv_rows.append({
            "DATA": tx.get("data"),
            "DÉBITO": debito,
            "CRÉDITO": credito,
            "HISTÓRICO DÉBITO": hist_debito,
            "HISTÓRICO CRÉDITO": hist_credito,
            "VALOR": valor
        })
    
    return pd.DataFrame(csv_rows)