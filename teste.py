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


    import streamlit as st
    import requests
    from bs4 import BeautifulSoup
    import re
    from datetime import datetime
    import sqlite3
    import pandas as pd

    # Dados de login das empresas
    dados_login_empresas = {
        'atual': {
            'cnpj': '07117654000149',
            'senhas': [' ', ' ', 'FOTUS23', 'FOTUS@'],
        },
    }

    # Criar um dataframe vazio para armazenar os resultados
    df_resultados = pd.DataFrame(columns=['Numero_Nota', 'Status', 'Data_Entrega', 'Previsao_Entrega'])

    class SSW_Consulta:
        def __init__(self):
            self.headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.5',
                'Cache-Control': 'max-age=0',
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://ssw.inf.br',
                'Referer': 'https://ssw.inf.br/2/rastreamento?',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Sec-GPC': '1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Brave";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }
            self.response_status = None

        def extrair_data_especifica(self, soup):
            elementos_tdb = soup.find_all('p', {'class': 'tdb'})

            for elemento in elementos_tdb:
                match = re.search(r'\b\d{2}/\d{2}/\d{2}\b', elemento.get_text())
                if match:
                    data_formatada = datetime.strptime(match.group(), '%d/%m/%y').strftime('%d/%m/%Y')
                    return data_formatada
            return "Data não encontrada"

        def realizar_consulta(self, data_login, numero_nota):
            data = {
                'cnpj': data_login['cnpj'],
                'NR': numero_nota,
                'chave': data_login['senhas'][0],
            }

            try:
                response = requests.post('https://ssw.inf.br/2/resultSSW', headers=self.headers, data=data)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                info_block = soup.find('tr', {'style': 'background-color:#FFFFFF;cursor:pointer;'})

                if info_block:
                    situacao_element = info_block.find('p', {'class': 'titulo'})
                    nf_element = info_block.find('p', {'class': 'tdb'})

                    url_completa = None
                    url_detalhes_element = info_block.find('a', {'class': 'email'})
                    if url_detalhes_element and 'onclick' in url_detalhes_element.attrs:
                        match = re.search(r"opx\('(.*?)'\)", url_detalhes_element['onclick'])
                        if match:
                            url_detalhes = match.group(1)
                            url_completa = f'https://ssw.inf.br{url_detalhes}'

                    if situacao_element and nf_element:
                        situacao_text = situacao_element.get_text(strip=True)
                        situacao_text = re.sub(r'\([^)]*\)', '', situacao_text)
                        nf_text = nf_element.get_text(strip=True)
                        data_situacao = self.extrair_data_especifica(soup)

                        # Extrair a previsão de entrega independentemente da situação
                        previsao_entrega = extrair_previsao_entrega(url_completa)
                        #st.write(f"Consultando Nota Fiscal: {numero_nota}")
                        #st.write(f"Situacao: {situacao_text}")
                        #st.write(f"data da entrega: {data_situacao}")
                        #st.write("Previsão de Entrega:", previsao_entrega)

                        # Adicionar resultados ao dataframe
                        df_resultados = pd.DataFrame({'Numero_Nota': [numero_nota],
                                                    'Status': [situacao_text],
                                                    'Data_Entrega': [data_situacao],
                                                    'Previsao_Entrega': [previsao_entrega]})
                        st.write("Resultados:", df_resultados)

                    else:
                        #st.write(f"Situacao: None")
                        #st.write(f"data da entrega: None")

                        # Adicionar resultados ao dataframe para situações onde a mercadoria não foi entregue
                        df_resultados = pd.DataFrame({'Numero_Nota': [numero_nota],
                                                    'Status': [None],
                                                    'Data_Entrega': [None],
                                                    'Previsao_Entrega': [None]})
                        st.write("Resultados:", df_resultados)

            except requests.RequestException as e:
                st.write(f"Erro na requisição: {e}")

            return None, None, None

        def realizar_consulta_com_senhas(self, data_login, numero_nota):
            for senha in data_login['senhas']:
                data_login['senhas'][0] = senha
                situacao, data_entrega, previsao_entrega = self.realizar_consulta(data_login, numero_nota)

                if situacao:
                    return situacao, data_entrega, previsao_entrega

            return None, None, None

    def extrair_previsao_entrega(url):
        try:
            response_detalhes = requests.get(url)
            response_detalhes.raise_for_status()
            soup_detalhes = BeautifulSoup(response_detalhes.text, 'html.parser')
            dados_detalhes = soup_detalhes.find_all(class_='tdb')

            if dados_detalhes:
                sexto_dado = dados_detalhes[7].text.strip()
                data_match = re.search(r'\d{2}/\d{2}/\d{2}', sexto_dado)

                if data_match:
                    previsao_entrega = data_match.group()
                    return previsao_entrega
                else:
                    #st.write("Data não encontrada no sexto dado.")
                    return None
            else:
                #st.write("Nenhum dado encontrado na classe 'tdb'")
                return None
        except requests.RequestException as e:
            #st.write(f"A solicitação falhou com o código de status {response_detalhes.status_code}: {e}")
            return None

    # Conectar ao banco de dados
    conn = sqlite3.connect('consultas.db')
    cursor = conn.cursor()

    # Criar o aplicativo Streamlit
    def main():
        st.title("Consulta de Notas Fiscais")

        if st.button("Iniciar Consulta"):
            # Consultar todas as linhas da tabela
            cursor.execute('SELECT Numero_Nota FROM consultas')
            numeros_notas = cursor.fetchall()

            # Loop através dos números de nota
            for numero_nota in numeros_notas:
                numero_nota = numero_nota[0]  # Extrair o valor do tuplo

                # Loop através dos dados de login das empresas
                for empresa, dados_login in dados_login_empresas.items():
                    consulta_ssw = SSW_Consulta()
                    situacao, data_situacao, previsao_entrega = consulta_ssw.realizar_consulta_com_senhas(dados_login, numero_nota)

                    if situacao:
                        # Adicionar resultados ao dataframe
                        df_resultados = pd.DataFrame({'Numero_Nota': [numero_nota],
                                                    'Status': [situacao],
                                                    'Data_Entrega': [data_situacao],
                                                    'Previsao_Entrega': [previsao_entrega]})
                        st.write("Resultados:", df_resultados)

                        cursor.execute("INSERT INTO consultas (Numero_Nota, Status, Data_Entrega, Previsao_Entrega) VALUES (?, ?, ?, ?)",
                                    (numero_nota, situacao, data_situacao, previsao_entrega))
                        conn.commit()

            st.success("Consulta concluída!")

            # Mostrar resultados no dataframe
            #st.write("Resultados:")
            st.write(df_resultados)

    # Executar o aplicativo
    if __name__ == '__main__':
        main()

    # Fechar a conexão com o banco de dados
    conn.close()




pages = {
    "Upload de dados": Coleta_Dados,
    "Atualizar plataforma": bot_final_page  

}

# Barra de navegação com as tabs
selected_page = st.sidebar.radio("Selecione uma página", list(pages.keys()))

# Exibir a página selecionada
pages[selected_page]()




