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
