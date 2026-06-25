import pandas as pd

def build_accounting_dataframe(raw_transactions):
    csv_rows = []
    
    for tx in raw_transactions:
        tipo = tx.get("tipo") 
        conta_contrapartida = tx.get("conta_classificada")
        
        # Pega exatamente o histórico do PDF e padroniza para letras maiúsculas
        historico = str(tx.get("historico")).upper().strip()
        
        # Formata o valor com duas casas decimais e troca o ponto por vírgula
        valor_float = float(tx.get("valor", 0))
        valor_formatado = f"{valor_float:.2f}".replace(".", ",")
        
        if tipo == "SAIDA":
            debito = conta_contrapartida
            credito = "BANCO"
        else: # ENTRADA
            debito = "BANCO"
            credito = conta_contrapartida
            
        csv_rows.append({
            "DATA": tx.get("data"),
            "DEBITO": debito,
            "CREDITO": credito,
            "HISTORICO": historico,
            "VALOR": valor_formatado
        })
    
    return pd.DataFrame(csv_rows)