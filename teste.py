import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime

st.set_page_config(
    page_title="Dona sorte",
    page_icon=":robot_face:",
    layout="wide",
    initial_sidebar_state="expanded"
)




class ConsultaNotas:
    def __init__(self, url, dados_login_empresa):
        self.url = url
        self.dados_login_empresa = dados_login_empresa





    def extrair_data_especifica(self,soup):
        # Encontrar todos os elementos <p> com a classe 'tdb'
        elementos_tdb = soup.find_all('p', {'class': 'tdb'})

        for elemento in elementos_tdb:
            # Procura pelo padrão "DD/MM/YY" no texto do elemento
            match = re.search(r'\b\d{2}/\d{2}/\d{2}\b', elemento.get_text())
            if match:
                data_formatada = datetime.strptime(match.group(), '%d/%m/%y').strftime('%d/%m/%Y')
                return data_formatada
        return "Data não encontrada"



    def obter_nome_mes(self, data):
        # Função para obter o nome do mês a partir da data no formato DD/MM/YYYY
        try:
            data_formatada = pd.to_datetime(data, errors='raise')
            nome_mes = data_formatada.strftime('%B').title()  # %B retorna o nome do mês por extenso
            # Mapear os nomes dos meses em inglês para português
            meses_ingles_portugues = {
                'January': 'Janeiro',
                'February': 'Fevereiro',
                'March': 'Março',
                'April': 'Abril',
                'May': 'Maio',
                'June': 'Junho',
                'July': 'Julho',
                'August': 'Agosto',
                'September': 'Setembro',
                'October': 'Outubro',
                'November': 'Novembro',
                'December': 'Dezembro',
            }
            return meses_ingles_portugues.get(nome_mes, '')
        except:
            return ''

    def calcular_percentual_frete(self, valor_frete, valor_total):
        # Função para calcular o percentual de frete
        if pd.notna(valor_frete) and pd.notna(valor_total) and valor_total != 0:
            percentual_frete = (valor_frete / valor_total) * 100
            return f"{percentual_frete:.2f}%"
        return ''


    def realizar_consulta_por_nota(self, nome_tabela, senha, numero_nota, df):
        payload = {
            'cnpj': self.dados_login_empresa[nome_tabela]['cnpj'],
            'NR': numero_nota,
            'chave': senha,
        }

        response = requests.post(self.url, data=payload)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            info_block = soup.find('tr', {'style': 'background-color:#FFFFFF;cursor:pointer;'})

            if info_block:
                situacao_element = info_block.find('p', {'class': 'titulo'})
                nf_element = info_block.find('p', {'class': 'tdb'})

                if situacao_element and nf_element:
                    situacao_text = situacao_element.get_text(strip=True)

                    # Remover conteúdo entre parênteses
                    situacao_text = re.sub(r'\([^)]*\)', '', situacao_text)

                    nf_text = nf_element.get_text(strip=True)
                    data_situacao = self.extrair_data_especifica(soup)

                    # Se a situação for "MERCADORIA ENTREGUE", então atualize a coluna 'DATA ENTREGA'
                    if "MERCADORIA ENTREGUE" in situacao_text:
                        df.loc[df['Nro. Nota'] == numero_nota, 'DATA ENTREGA'] = data_situacao

                    df.loc[df['Nro. Nota'] == numero_nota, 'STATUS'] = situacao_text

                    # Exibir o DataFrame atualizado após cada consulta
                    dataframe_atualizado.dataframe(df.tail(100000)) 

                else:
                    st.write(f'Elementos de situação, NF ou data não encontrados para {nome_tabela} - Nota {numero_nota}')
            else:
                st.write(f'Bloco de informações não encontrado para {nome_tabela} - Nota {numero_nota}')
        else:
            st.write(f'Erro no login para {nome_tabela} - Nota {numero_nota}')



    def atualizar_colunas(self, df):
        # Atualizando a coluna 'MÊS' com base na coluna 'Data de Saída'
        df['MÊS'] = df['Data de Saída'].apply(self.obter_nome_mes)

        # Atualizando a coluna 'Região' com base na coluna 'UF'
        df['Região'] = df['UF'].apply(self.obter_regiao)

        # Adicionando a coluna '%Frete'
        df['Perc.Frete'] = df.apply(lambda row: self.calcular_percentual_frete(row['VALOR FRETE'], row['Valor Total']), axis=1)

        df['DATA STATUS'] = datetime.now().strftime('%d/%m/%Y')

 


    def obter_regiao(self, uf):
        # Mapeando a região com base na UF
        regioes = {
            'AC': 'NORTE',
            'AL': 'NORDESTE',
            'AP': 'NORTE',

            'AM': 'NORTE',
            'BA': 'NORDESTE',
            'CE': 'NORDESTE',
            'DF': 'CENTRO-OESTE',
            'ES': 'SUDESTE',
            'GO': 'CENTRO-OESTE',
            'MA': 'NORDESTE',
            'MT': 'CENTRO-OESTE',
            'MS': 'CENTRO-OESTE',
            'MG': 'SUDESTE',
            'PA': 'NORTE',
            'PB': 'NORDESTE',
            'PR': 'SUL',
            'PE': 'NORDESTE',
            'PI': 'NORDESTE',
            'RJ': 'SUDESTE',
            'RN': 'NORDESTE',
            'RS': 'SUL',
            'RO': 'NORTE',
            'RR': 'NORTE',
            'SC': 'SUL',
            'SP': 'SUDESTE',
            'SE': 'NORDESTE',
            'TO': 'NORTE',
        }

        return regioes.get(uf, 'Região não encontrada')

    def realizar_consultas(self, tabela_selecionada, df):
        senha_empresa_selecionada = self.dados_login_empresa.get(tabela_selecionada, {}).get('senha', '')

        if not senha_empresa_selecionada:
            st.write(f'Senha não encontrada para {tabela_selecionada}')
            return

        # Filtrando as notas para a tabela selecionada
        notas_selecionadas = df.loc[df['Transportadora'] == tabela_selecionada, 'Nro. Nota'].unique().tolist()

        # Iterando sobre as notas e realizando as consultas
        for numero_nota in notas_selecionadas:
            self.realizar_consulta_por_nota(tabela_selecionada, senha_empresa_selecionada, numero_nota, df)
            time.sleep(5)  # Atraso de 5 segundos entre as consultas



# URL para consulta
url = 'https://ssw.inf.br/2/resultSSW'

# Dados de login para empresas
dados_login_empresa = {
    'TG TRANSPORTES GERAIS E DISTRIBUICAO LTDA': {
        'cnpj': '07117654000149',
        'senha': 'MAIORALT',
    },
    'FITLOG TRANSPORTES E LOGISTICA': {
        'cnpj': '07117654000149',
        'senha': 'FOTUS23',
    },
    'CT DISTRIBUICAO E LOGISTICA LTDA': {
        'cnpj': '07117654000149',
        'senha': 'FOTUS@',
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
    # Corrigindo o nome da coluna após renomeação
    df['Nro. Nota'] = df['Nro. Nota'].astype(str).str.replace('.', '')



    # Removendo o último caractere de cada valor na coluna 'Nro. Nota'
    df['Nro. Nota'] = df['Nro. Nota'].astype(str).apply(lambda x: x[:-1] if x.isdigit() else x)

    # Atualizando as colunas 'MÊS', 'Região' e adicionando a coluna '%Frete'
    consulta_notas.atualizar_colunas(df)

    # Formatando as colunas de datas
    df['Data de Saída'] = pd.to_datetime(df['Data de Saída'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['PREVISÃO DE ENTREGA'] = pd.to_datetime(df['PREVISÃO DE ENTREGA'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['DATA ENTREGA'] = pd.to_datetime(df['DATA ENTREGA'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['DATA STATUS'] = pd.to_datetime(df['DATA STATUS'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['Dt.Faturamento'] = pd.to_datetime(df['Dt.Faturamento'], errors='coerce').dt.strftime('%d/%m/%Y')



    # ... (seu código existente)
    # Seleção da tabela
    tabelas = df['Transportadora'].unique().tolist()  # Adicione mais tabelas conforme necessário
    tabela_selecionada = st.selectbox('Selecione a transportadora:', tabelas)

    dataframe_atualizado = st.empty()  # Este é o espaço reservado para o DataFrame


    # Botão para realizar as consultas
    if st.button('Realizar Consultas') and tabela_selecionada:
        consulta_notas.realizar_consultas(tabela_selecionada, df)
