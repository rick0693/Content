import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import streamlit as st
import time

class ConsultaNotas:
    def __init__(self, url, dados_login_empresa):
        self.url = url
        self.dados_login_empresa = dados_login_empresa

    def extrair_data_especifica(self, soup):
        elementos_tdb = soup.find_all('p', {'class': 'tdb'})
        for elemento in elementos_tdb:
            match = re.search(r'\b\d{2}/\d{2}/\d{2}\b', elemento.get_text())
            if match:
                return match.group()
        return "Data não encontrada"

    def realizar_consulta_por_nota(self, nome_tabela, senha, numero_nota):
        payload = {
            'cnpj': self.dados_login_empresa[nome_tabela]['cnpj'],
            'NR': numero_nota,
            'chave': senha,
        }

        response = requests.post(self.url, data=payload)

        if response.status_code == 200:
            st.write(f'Login realizado para {nome_tabela} - Nota {numero_nota}')
            soup = BeautifulSoup(response.text, 'html.parser')
            info_block = soup.find('tr', {'style': 'background-color:#FFFFFF;cursor:pointer;'})

            if info_block:
                situacao_element = info_block.find('p', {'class': 'titulo'})
                nf_element = info_block.find('p', {'class': 'tdb'})

                if situacao_element and nf_element:
                    situacao_text = situacao_element.get_text(strip=True)
                    nf_text = nf_element.get_text(strip=True)
                    data_situacao = self.extrair_data_especifica(soup)

                    st.write(f'Situação da Mercadoria: {situacao_text}')
                    st.write(f'NF: {nf_text}')
                    st.write(f'Data: {data_situacao}')
                    st.write('-' * 40)
                else:
                    st.write(f'Elementos de situação, NF ou data não encontrados para {nome_tabela} - Nota {numero_nota}')
            else:
                st.write(f'Bloco de informações não encontrado para {nome_tabela} - Nota {numero_nota}')
        else:
            st.write(f'Erro no login para {nome_tabela} - Nota {numero_nota}')

    def realizar_consultas(self, tabela_selecionada, df):
        senha_empresa_selecionada = self.dados_login_empresa.get(tabela_selecionada, {}).get('senha', '')

        if not senha_empresa_selecionada:
            st.write(f'Senha não encontrada para {tabela_selecionada}')
            return

        # Filtrando as notas para a tabela selecionada
        notas_selecionadas = df.loc[df['Transportadora'] == tabela_selecionada, 'Nro. Nota'].unique().tolist()

        # Iterando sobre as notas e realizando as consultas
        for numero_nota in notas_selecionadas:
            self.realizar_consulta_por_nota(tabela_selecionada, senha_empresa_selecionada, numero_nota)
            time.sleep(5)  # Atraso de 5 segundos entre as consultas

# URL para consulta
url = 'https://ssw.inf.br/2/resultSSW'

# Dados de login para empresas
dados_login_empresa = {
    'TG TRANSPORTES GERAIS E DISTRIBUICAO LTDA': {
        'cnpj': '07117654000149',
        'senha': 'MAIORALT',
    },
    # Adicione mais empresas conforme necessário
}

# Instância da classe de consulta
consulta_notas = ConsultaNotas(url, dados_login_empresa)

# Upload da planilha
uploaded_file = st.file_uploader("Escolha um arquivo XLSX", type="xlsx")

# Botão para realizar as consultas após o upload
if uploaded_file is not None:
    # Lendo a planilha Excel
    df = pd.read_excel(uploaded_file)

    # Renomeando as colunas para corresponder à estrutura desejada
    df.rename(columns={
        'NUMERO_NOTA': 'Nro. Nota',
        'NUMERO_FOTUS': 'Nº Fotus',
        'PREVISÃO DE ENTREGA': 'PREVISÃO DE ENTREGA',
        'DATA ENTREGA': 'DATA ENTREGA',
        'DATA STATUS': 'DATA STATUS',
        
        # Adicione mais renomeações conforme necessário
    }, inplace=True)

    # Ajustando o formato da coluna "Nº Fotus" conforme sua expressão
    df['Nº Fotus'] = df['Nº Fotus'].apply(lambda x: f"{str(int(x))[:-2]}-{str(int(x))[-2:]}" if not pd.isna(x) else "")

    # Removendo os pontos da coluna "Nro. Nota"
    df['Nro. Nota'] = df['Nro. Nota'].astype(str).str.replace('.', '')



    # Removendo o último caractere de cada valor na coluna 'Nro. Nota'
    df['Nro. Nota'] = df['Nro. Nota'].astype(str).apply(lambda x: x[:-1] if x.isdigit() else x)



    # Formatando as colunas de datas
    df['Data de Saída'] = pd.to_datetime(df['Data de Saída'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['PREVISÃO DE ENTREGA'] = pd.to_datetime(df['PREVISÃO DE ENTREGA'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['DATA ENTREGA'] = pd.to_datetime(df['DATA ENTREGA'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['DATA STATUS'] = pd.to_datetime(df['DATA STATUS'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['Dt.Faturamento'] = pd.to_datetime(df['Dt.Faturamento'], errors='coerce').dt.strftime('%d/%m/%Y')


    # Exibir o DataFrame
    st.write("DataFrame Carregado:")
    st.write(df)

    # Seleção da tabela
    tabelas = df['Transportadora'].unique().tolist()  # Adicione mais tabelas conforme necessário
    tabela_selecionada = st.selectbox('Selecione a transportadora:', tabelas)

    # Botão para realizar as consultas
    if st.button('Realizar Consultas') and tabela_selecionada:
        consulta_notas.realizar_consultas(tabela_selecionada, df)
