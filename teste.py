import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
import sqlite3

st.set_page_config(
    page_title="Dona sorte",
    page_icon=":robot_face:",
    layout="wide",
    initial_sidebar_state="expanded"
)

class ConsultaNotas:
    def __init__(self, url, dados_login_empresa, db_filename='consultas.db'):
        self.url = url
        self.dados_login_empresa = dados_login_empresa
        self.db_filename = db_filename

        # Criar a tabela no banco de dados se não existir
        self._criar_tabela_consultas()

    def _criar_tabela_consultas(self):
        conn = sqlite3.connect(self.db_filename)
        cursor = conn.cursor()

        # Ajuste conforme suas colunas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tabela TEXT,  -- Adicione a coluna 'tabela'
                Nro_Fotus TEXT,
                Data_Saida TEXT,
                MES TEXT,
                UF TEXT,
                Regiao TEXT,
                Numero_Nota TEXT,
                Valor_Total TEXT,
                Valor_Frete TEXT,
                Peso TEXT,
                Perc_Frete TEXT,
                Transportadora TEXT,
                Dt_Faturamento TEXT,
                PLATAFORMA TEXT,
                Previsao_Entrega TEXT,
                Data_Entrega TEXT,
                Data_Status TEXT,
                STATUS TEXT,
                Situacao_Entrega TEXT,
                Leadtime TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def extrair_data_especifica(self, soup):
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
        # Função para obter o nome do MES a partir da data no formato DD/MM/YYYY
        try:
            data_formatada = pd.to_datetime(data, errors='raise')
            nome_mes = data_formatada.strftime('%B').title()  # %B retorna o nome do MES por extenso
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

    def salvar_resultados_consulta(self, tabela, df):
        conn = sqlite3.connect(self.db_filename)
        cursor = conn.cursor()

        for _, row in df.iterrows():
            nota = row['Numero_Nota']
            status = row['STATUS']
            data_entrega = row['Data_Entrega'] if 'Data_Entrega' in row else None  # Ajuste conforme suas colunas

            # Adicionar a consulta ao banco de dados
            cursor.execute('''
                INSERT INTO consultas (
                    Nro_Fotus, Data_Saida, MES, UF, Regiao, Numero_Nota, Valor_Total,
                    Valor_Frete, Peso, Perc_Frete, Transportadora, Dt_Faturamento,
                    PLATAFORMA, Previsao_Entrega, Data_Entrega, Data_Status, STATUS,
                    Situacao_Entrega, Leadtime, tabela
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['Nro_Fotus'], row['Data_Saida'], row['MES'], row['UF'],
                row['Regiao'], row['Numero_Nota'], row['Valor_Total'],
                row['Valor_Frete'], row['Peso'], row['Perc_Frete'],
                row['Transportadora'], row['Dt_Faturamento'],
                row['PLATAFORMA'], row['Previsao_Entrega'], row['Data_Entrega'],
                row['Data_Status'], row['STATUS'], row['Situacao_Entrega'], row['Leadtime'],
                tabela
            ))

        conn.commit()
        conn.close()

    def realizar_consulta_por_nota(self, nome_tabela, senha, Numero_Nota, df):
        payload = {
            'cnpj': self.dados_login_empresa[nome_tabela]['cnpj'],
            'NR': Numero_Nota,
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
                situacao_text = re.sub(r'\([^)]*\)', '', situacao_text)
                nf_text = nf_element.get_text(strip=True)
                data_situacao = self.extrair_data_especifica(soup)

                # Atualize a coluna 'Data_Entrega' se a situação for "MERCADORIA ENTREGUE"
                if "MERCADORIA ENTREGUE" in situacao_text:
                    df.loc[df['Numero_Nota'] == Numero_Nota, 'Data_Entrega'] = data_situacao

                    # Atualize a coluna 'Situacao_Entrega' com base nas condições fornecidas
                    df.loc[df['Numero_Nota'] == Numero_Nota, 'Situacao_Entrega'] = self.atualizar_situacao_entrega(df, Numero_Nota)

                df.loc[df['Numero_Nota'] == Numero_Nota, 'STATUS'] = situacao_text

                # Verificar se há diferenças entre os dados existentes no banco e os novos dados
                dados_banco = self.obter_dados_consulta(nome_tabela, Numero_Nota)
                if dados_banco is not None and not dados_banco.equals(df[df['Numero_Nota'] == Numero_Nota]):
                    # Se houver diferenças, atualizar os dados no banco
                    self.atualizar_dados_consulta(nome_tabela, Numero_Nota, df)

        # Exibir o DataFrame atualizado após cada consulta
        dataframe_atualizado.dataframe(df.tail(100000000))
        st.write("Resultados salvos no banco de dados.")

    def obter_dados_consulta(self, tabela, Numero_Nota):
        conn = sqlite3.connect(self.db_filename)
        query = f"SELECT * FROM consultas WHERE tabela = '{tabela}' AND Numero_Nota = '{Numero_Nota}'"
        dados_banco = pd.read_sql_query(query, conn)
        conn.close()
        return dados_banco

    def atualizar_dados_consulta(self, tabela, Numero_Nota, df):
        conn = sqlite3.connect(self.db_filename)
        cursor = conn.cursor()

        for _, row in df[df['Numero_Nota'] == Numero_Nota].iterrows():
            cursor.execute('''
                UPDATE consultas SET
                    Nro_Fotus = ?,
                    Data_Saida = ?,
                    MES = ?,
                    UF = ?,
                    Regiao = ?,
                    Valor_Total = ?,
                    Valor_Frete = ?,
                    Peso = ?,
                    Perc_Frete = ?,
                    Transportadora = ?,
                    Dt_Faturamento = ?,
                    PLATAFORMA = ?,
                    Previsao_Entrega = ?,
                    Data_Entrega = ?,
                    Data_Status = ?,
                    STATUS = ?,
                    Situacao_Entrega = ?,
                    Leadtime = ?
                WHERE tabela = ? AND Numero_Nota = ?
            ''', (
                row['Nro_Fotus'], row['Data_Saida'], row['MES'], row['UF'],
                row['Regiao'], row['Valor_Total'], row['Valor_Frete'], row['Peso'],
                row['Perc_Frete'], row['Transportadora'], row['Dt_Faturamento'],
                row['PLATAFORMA'], row['Previsao_Entrega'], row['Data_Entrega'],
                row['Data_Status'], row['STATUS'], row['Situacao_Entrega'],
                row['Leadtime'], tabela, Numero_Nota
            ))

        conn.commit()
        conn.close()

    def atualizar_situacao_entrega(self, df, Numero_Nota):
        # Função para atualizar a coluna 'Situacao_Entrega'
        previsao_entrega = df.loc[df['Numero_Nota'] == Numero_Nota, 'Previsao_Entrega'].values[0]
        data_entrega = df.loc[df['Numero_Nota'] == Numero_Nota, 'Data_Entrega'].values[0]

        if pd.notna(data_entrega):
            if data_entrega > previsao_entrega:
                return "ENTREGUE FORA DO PRAZO"
            else:
                return "ENTREGUE NO PRAZO"
        elif pd.notna(previsao_entrega) and previsao_entrega < datetime.now().strftime('%d/%m/%Y'):
            return "EM TRANSITO ATRASADO"
        else:
            return "EM TRANSITO"

    def atualizar_colunas(self, df):
        # Atualizando a coluna 'MES ' com base na coluna 'Data_Saida'
        df['MES '] = df['Data_Saida'].apply(self.obter_nome_mes)

        # Atualizando a coluna 'Regiao' com base na coluna 'UF'
        df['Regiao'] = df['UF'].apply(self.obter_regiao)

        # Adicionando a coluna '%Frete'
        df['Perc.Frete'] = df.apply(lambda row: self.calcular_percentual_frete(row['Valor_Frete'], row['Valor_Total']), axis=1)

        df['Data_Status'] = datetime.now().strftime('%d/%m/%Y')

    def obter_regiao(self, uf):
        # Mapeando a Regiao com base na UF
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

        return regioes.get(uf, 'Regiao não encontrada')

    def realizar_consultas(self, tabela_selecionada, df):
        senha_empresa_selecionada = self.dados_login_empresa.get(tabela_selecionada, {}).get('senha', '')

        if not senha_empresa_selecionada:
            st.write(f'Senha não encontrada para {tabela_selecionada}')
            return

        # Filtrando as notas para a tabela selecionada
        notas_selecionadas = df.loc[df['Transportadora'] == tabela_selecionada, 'Numero_Nota'].unique().tolist()

        # Iterando sobre as notas e realizando as consultas
        for Numero_Nota in notas_selecionadas:
            self.realizar_consulta_por_nota(tabela_selecionada, senha_empresa_selecionada, Numero_Nota, df)
            time.sleep(5)  # Atraso de 5 segundos entre as consultas

# URL para consulta
url = 'https://ssw.inf.br/2/resultSSW'

# Dados de login para empresas
dados_login_empresa = {
    'TG TRANSPORTES GERAIS E DISTRIBUICAO LTDA': {
        'cnpj': '07117654000149',
        'senha': 'MAIORALT',
    },
    'TENHOMOVEIS COMERCIO DE MOVEIS E UTENSILIOS DOMESTICOS LTDA': {
        'cnpj': '07117654000149',
        'senha': ' ',
    },
    'CT DISTRIBUICAO E LOGISTICA LTDA': {
        'cnpj': '07117654000149',
        'senha': 'FOTUS@',
    },
    # Adicione mais empresas conforme necessário
}

# Instância da classe de consulta
consulta_notas = ConsultaNotas(url, dados_login_empresa)

# Função para carregar os dados e realizar consultas
@st.cache_data
def load_and_process_data(uploaded_file):
    df = pd.read_excel(uploaded_file)

    # Renomeando as colunas para corresponder à estrutura desejada
    df.rename(columns={
        'Numero_Nota': 'Numero_Nota',
        'Nro_Fotus': 'Nro_Fotus',
        'Previsao_Entrega': 'Previsao_Entrega',
        'Data_Entrega': 'Data_Entrega',
        'Data_Status': 'Data_Status',
        # Adicione mais renomeações conforme necessário
    }, inplace=True)

    # Ajustando o formato da coluna "Nro_Fotus" conforme sua expressão
    df['Nro_Fotus'] = df['Nro_Fotus'].apply(lambda x: f"{str(int(x))[:-2]}-{str(int(x))[-2:]}" if not pd.isna(x) else "")

    # Removendo os pontos da coluna "Numero_Nota"
    # Corrigindo o nome da coluna após renomeação
    df['Numero_Nota'] = df['Numero_Nota'].astype(str).str.replace('.', '')

    # Removendo o último caractere de cada valor na coluna 'Numero_Nota'
    df['Numero_Nota'] = df['Numero_Nota'].astype(str).apply(lambda x: x[:-1] if x.isdigit() else x)

    # Atualizando as colunas 'MES ', 'Regiao' e adicionando a coluna '%Frete'
    consulta_notas.atualizar_colunas(df)

    # Formatando as colunas de datas
    df['Data_Saida'] = pd.to_datetime(df['Data_Saida'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['Previsao_Entrega'] = pd.to_datetime(df['Previsao_Entrega'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['Data_Entrega'] = pd.to_datetime(df['Data_Entrega'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['Data_Status'] = pd.to_datetime(df['Data_Status'], errors='coerce').dt.strftime('%d/%m/%Y')
    df['Dt_Faturamento'] = pd.to_datetime(df['Dt_Faturamento'], errors='coerce').dt.strftime('%d/%m/%Y')

    return df

# Upload da planilha
uploaded_file = st.file_uploader("Escolha um arquivo XLSX", type="xlsx")

# Botão para realizar as consultas após o upload
if uploaded_file is not None:
    df = load_and_process_data(uploaded_file)

    # ... (seu código existente)

    # Seleção da tabela
    tabelas = df['Transportadora'].unique().tolist()  # Adicione mais tabelas conforme necessário
    tabela_selecionada = st.selectbox('Selecione a transportadora:', tabelas)

    dataframe_atualizado = st.empty()  # Este é o espaço reservado para o DataFrame

    # Botão para realizar as consultas
    if st.button('Realizar Consultas') and tabela_selecionada:
        consulta_notas.realizar_consultas(tabela_selecionada, df)
