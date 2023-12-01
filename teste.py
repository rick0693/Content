import pandas as pd
import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st
import sqlite3
from datetime import datetime
import streamlit as st
import requests
import sqlite3
from time import sleep

st.set_page_config(
    page_title="Consulta_SSW",
    page_icon=":robot_face:",
    layout="wide",
    initial_sidebar_state="expanded"
)



# Função para a página de Notícias
def Coleta_Dados():

    class ConsultaNotas:
        def __init__(self, db_filename='consultas.db'):
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

        def salvar_resultados_consulta(self, df):
            conn = sqlite3.connect(self.db_filename)
            cursor = conn.cursor()

            # Limpar todos os registros da tabela
            cursor.execute('DELETE FROM consultas')

            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT INTO consultas (
                        Nro_Fotus, Data_Saida, MES, UF, Regiao, Numero_Nota, Valor_Total,
                        Valor_Frete, Peso, Perc_Frete, Transportadora, Dt_Faturamento,
                        PLATAFORMA, Previsao_Entrega, Data_Entrega, Data_Status, STATUS,
                        Situacao_Entrega, Leadtime
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['Nro_Fotus'], row['Data_Saida'], row['MES'], row['UF'],
                    row['Regiao'], row['Numero_Nota'], row['Valor_Total'],
                    row['Valor_Frete'], row['Peso'], row['Perc_Frete'],
                    row['Transportadora'], row['Dt_Faturamento'],
                    row['PLATAFORMA'], row['Previsao_Entrega'], row['Data_Entrega'],
                    row['Data_Status'], row['STATUS'], row['Situacao_Entrega'], row['Leadtime']
                ))

            conn.commit()
            conn.close()

    # URL para consulta

    # Instância da classe de consulta
    consulta_notas = ConsultaNotas()

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
        df['Nro_Fotus'] = df['Nro_Fotus'].apply(lambda x: f"0{str(int(x))[:-2]}-{str(int(x))[-2:]}" if not pd.isna(x) else "")


        # Removendo os pontos da coluna "Numero_Nota"
        # Corrigindo o nome da coluna após renomeação
        df['Numero_Nota'] = df['Numero_Nota'].astype(str).str.replace('.', '')


        # Atualizando as colunas 'MES ', 'Regiao' e adicionando a coluna '%Frete'
        df = atualizar_colunas(df)

        # Formatando as colunas de datas
        df['Data_Saida'] = pd.to_datetime(df['Data_Saida'], errors='coerce').dt.strftime('%d/%m/%Y')
        df['Previsao_Entrega'] = pd.to_datetime(df['Previsao_Entrega'], errors='coerce').dt.strftime('%d/%m/%Y')
        df['Data_Entrega'] = pd.to_datetime(df['Data_Entrega'], errors='coerce').dt.strftime('%d/%m/%Y')
        df['Data_Status'] = pd.to_datetime(df['Data_Status'], errors='coerce').dt.strftime('%d/%m/%Y')
        df['Dt_Faturamento'] = pd.to_datetime(df['Dt_Faturamento'], errors='coerce').dt.strftime('%d/%m/%Y')

        # Salvar resultados no banco de dados
        consulta_notas.salvar_resultados_consulta(df)

        return df

    def atualizar_colunas(df):
        # Atualizando a coluna 'MES ' com base na coluna 'Data_Saida'
        df['MES '] = df['Data_Saida'].apply(obter_nome_mes)

        # Atualizando a coluna 'Regiao' com base na coluna 'UF'
        df['Regiao'] = df['UF'].apply(obter_regiao)

        # Adicionando a coluna '%Frete'
        df['Perc.Frete'] = df.apply(lambda row: calcular_percentual_frete(row['Valor_Frete'], row['Valor_Total']), axis=1)

        df['Data_Status'] = datetime.now().strftime('%d/%m/%Y')

        return df

    def obter_nome_mes(data):
        # Função para obter o nome do MES a partir da data no formato DD/MM/YYYY
        try:
            data_formatada = pd.to_datetime(data, errors='raise')
            nome_mes = data_formatada.strftime('%B').title()  # %B retorna o nome do MES por extenso
            # Mapear os nomes dos meses em inglês para português
            meses_ingles_portugues = {
                'January': 'Janeiro',
                'February': 'Fevereiro',
                # Adicione mais meses conforme necessário
            }
            return meses_ingles_portugues.get(nome_mes, '')
        except:
            return ''

    def calcular_percentual_frete(valor_frete, valor_total):
        # Função para calcular o percentual de frete
        if pd.notna(valor_frete) and pd.notna(valor_total) and valor_total != 0:
            percentual_frete = (valor_frete / valor_total) * 100
            return f"{percentual_frete:.2f}%"
        return ''

    def obter_regiao(uf):
        # Mapeando a Regiao com base na UF
        regioes = {
            'AC': 'NORTE',
            # Adicione mais mapeamentos conforme necessário
        }

        return regioes.get(uf, 'Regiao não encontrada')

    # Upload da planilha
    uploaded_file = st.file_uploader("Escolha um arquivo XLSX", type="xlsx")

    # Botão para realizar as consultas após o upload
    if uploaded_file is not None:
        df = load_and_process_data(uploaded_file)

        # Exibir o DataFrame atualizado após o upload
        st.write(df)

# Função para a página de Dados
def bot_final_page():



    # Função para realizar as consultas
    def realizar_consultas():
        # Conectar ao banco de dados
        conn = sqlite3.connect('consultas.db')
        cursor = conn.cursor()

        # Consultar todas as linhas da tabela
        cursor.execute('SELECT Nro_Fotus, plataforma FROM consultas')
        resultados = cursor.fetchall()

        # Loop através dos resultados
        for resultado in resultados:
            Nro_Fotus, plataforma = resultado

            # Lógica para determinar o valor da variável acao com base na plataforma
            if plataforma == 'ENTREGUE':
                ACAO = 4
            elif plataforma == 'COLETADO':
                ACAO = 3
            else:
                # Se a plataforma não for 'ENTREGUE' nem 'COLETADO', imprima uma mensagem e pule para a próxima iteração
                st.toast(f"Plataforma não reconhecida para Nro_Fotus {Nro_Fotus}. Pulando para a próxima iteração.")
                continue

            # Imprimir informações antes de realizar a consulta
            st.toast(f"Consultando Nro_Fotus: {Nro_Fotus}, Plataforma: {plataforma}, Ação: {ACAO}")

            # Restante do código permanece o mesmo
            headers = {
                'authority': 'app.fotus.com.br',
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lIjoiUmljYXJkbyBTYW50b3MiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiJWZW5kZWRvciIsImh0dHA6Ly9zY2hlbWFzLnhtbHNvYXAub3JnL3dzLzIwMDUvMDUvaWRlbnRpdHkvY2xhaW1zL2VtYWlsYWRkcmVzcyI6InJpY2FyZG8uc2FudG9zQGZvdHVzLmNvbS5iciIsImV4cCI6MTcwMTM5ODA5NSwiaXNzIjoiZmFicmljYV9naSIsImF1ZCI6ImV2ZXJlc3RfZ2kifQ.rFyENS6NX8Yy_9RjaBGFvvSB-PVKi8rK7ukyGGM5yEk',
                'cache-control': 'no-cache, no-store, must-revalidate',
                'content-type': 'application/json',
                'expires': '0',
                'origin': 'https://app.fotus.com.br',
                'pragma': 'no-cache',
                'referer': 'https://app.fotus.com.br/monitoramento-expedicao',
                'sec-ch-ua': '"Brave";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'sec-gpc': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            }
            json_data = {
                'idCupom': Nro_Fotus,
                'acao': ACAO,
            }

            response = requests.post('https://app.fotus.com.br/API/api/Etapa/SalvarHistorico', headers=headers, json=json_data)

            # Adicionar atraso de 2 segundos entre cada solicitação
            sleep(2)

            # Note: json_data will not be serialized by requests exactly as it was in the original request.
            # data = '{"idCupom":"0298066-98","acao":4}'
            # response = requests.post('https://app.fotus.com.br/API/api/Etapa/SalvarHistorico', headers=headers, data=data)

            # Imprimir informações após a consulta
            if response.status_code == 200:
                st.toast(f"Consulta bem-sucedida para Nro_Fotus {Nro_Fotus}", icon="✅")
            else:
                st.toast(f"Falha na consulta para Nro_Fotus {Nro_Fotus}")

        # Fechar a conexão com o banco de dados
        conn.close()

    # Página Streamlit
    st.title("Aplicativo de Consultas")

    # Botão para iniciar as consultas
    if st.button("Iniciar Consultas"):
        realizar_consultas()

pages = {
    "Upload de dados": Coleta_Dados,
    "Atualizar plataforma": bot_final_page  

}

# Barra de navegação com as tabs
selected_page = st.sidebar.radio("Selecione uma página", list(pages.keys()))

# Exibir a página selecionada
pages[selected_page]()




