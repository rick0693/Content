        if info_block:
            situacao_element = info_block.find('p', {'class': 'titulo'})
            nf_element = info_block.find('p', {'class': 'tdb'})

            if situacao_element and nf_element:
                situacao_text = situacao_element.get_text(strip=True)
                situacao_text = re.sub(r'\([^)]*\)', '', situacao_text)
                nf_text = nf_element.get_text(strip=True)
                data_situacao = self.extrair_data_especifica(soup)

                # Atualize a coluna 'DATA ENTREGA' se a situação for "MERCADORIA ENTREGUE"
                if "MERCADORIA ENTREGUE" in situacao_text:
                    df.loc[df['Nro. Nota'] == numero_nota, 'DATA ENTREGA'] = data_situacao

                    # Atualize a coluna 'SITUAÇÃO DA ENTREGA' com base nas condições fornecidas
                    df.loc[df['Nro. Nota'] == numero_nota, 'SITUAÇÃO DA ENTREGA'] = self.atualizar_situacao_entrega(df, numero_nota)

                df.loc[df['Nro. Nota'] == numero_nota, 'STATUS'] = situacao_text

                # Exibir o DataFrame atualizado após cada consulta
                dataframe_atualizado.dataframe(df.tail(100))
            else:
                st.write(f'Elementos de situação, NF ou data não encontrados para {nome_tabela} - Nota {numero_nota}')
        else:
            st.write(f'Bloco de informações não encontrado para {nome_tabela} - Nota {numero_nota}')

    def atualizar_situacao_entrega(self, df, numero_nota):
        # Função para atualizar a coluna 'SITUAÇÃO DA ENTREGA'
        previsao_entrega = df.loc[df['Nro. Nota'] == numero_nota, 'PREVISÃO DE ENTREGA'].values[0]
        data_entrega = df.loc[df['Nro. Nota'] == numero_nota, 'DATA ENTREGA'].values[0]

        if pd.notna(data_entrega):
            if data_entrega > previsao_entrega:
                return "ENTREGUE FORA DO PRAZO"
            else:
                return "ENTREGUE NO PRAZO"
        elif pd.notna(previsao_entrega) and previsao_entrega < datetime.now().strftime('%d/%m/%Y'):
            return "EM TRANSITO ATRASADO"
        else:
            return "EM TRANSITO"
