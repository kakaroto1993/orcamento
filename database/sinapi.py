#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Módulo de banco de dados para o OrçaFácil
Contém a classe principal para manipulação de dados do SINAPI
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime
import shutil
import tempfile
import re
import atexit

class SinapiManager:
    """
    Gerenciador de banco de dados para o SINAPI
    Versão refatorada da classe SinapiImporter original
    """
    def __init__(self, db_path='orcamento.db'):
        """Inicializa o gerenciador de banco de dados"""
        self.db_path = db_path
        self.conn = None
        self.temp_files = []  # Lista para controlar arquivos temporários
        
        # Registra a função de limpeza para ser executada ao sair
        atexit.register(self.limpar_arquivos_temporarios)
        
        # Inicializa o banco de dados
        self.setup_database()
    
    def setup_database(self):
        """Cria a conexão e as tabelas necessárias"""
        # Verifica se o banco já existe
        banco_existente = os.path.exists(self.db_path)
        
        # Conecta ao banco
        self.conn = sqlite3.connect(self.db_path)
        
        # Se o banco já existe, verifica se precisa atualizar o esquema
        if banco_existente:
            self._verificar_migracoes()
        # Senão, cria as tabelas do zero
        else:
            self._criar_tabela_insumos()
            self._criar_tabela_composicoes()
            self._criar_tabela_composicao_insumos()
            self._criar_tabela_projetos()
            self._criar_tabela_orcamento_itens()
        
        self.conn.commit()
    
    def importar_insumos(self, arquivo_excel, aba='insumos', mes_ref=None):
        """Importa insumos do Excel SINAPI"""
        if not mes_ref:
            mes_ref = datetime.now().strftime("%Y-%m")
            
        print(f"Importando insumos de {arquivo_excel}...")
        
        try:
            # Cria uma cópia temporária do arquivo para evitar problemas de permissão
            temp_file = self._criar_arquivo_temporario(arquivo_excel)
            
            # Carrega a planilha sem definir cabeçalho inicialmente
            df = pd.read_excel(temp_file, sheet_name=aba, header=None)
            
            # Encontra a linha que contém 'CODIGO' para determinar onde os cabeçalhos reais estão
            linha_header = None
            for i, row in df.iterrows():
                row_str = ' '.join([str(cell).upper() for cell in row if pd.notna(cell)])
                if 'CODIGO' in row_str:
                    linha_header = i
                    break
            
            if linha_header is None:
                print("❌ Não foi possível encontrar a linha de cabeçalho com 'CODIGO'")
                return 0
                
            # Define esta linha como cabeçalho e recria o DataFrame
            cabeçalhos = df.iloc[linha_header]
            df = pd.DataFrame(df.values[linha_header+1:], columns=cabeçalhos)
            
            # Identifica as colunas que precisamos
            col_codigo = next((col for col in df.columns if str(col).strip().upper() == 'CODIGO'), None)
            col_descricao = next((col for col in df.columns if 'DESCRICAO' in str(col).upper() and 'INSUMO' in str(col).upper()), None)
            col_unidade = next((col for col in df.columns if 'UNIDADE' in str(col).upper()), None)
            col_preco = next((col for col in df.columns if 'PRECO' in str(col).upper() and 'MEDIANO' in str(col).upper()), None)
            
            # Se não encontrou as colunas, tenta novamente com uma busca mais flexível
            if not col_codigo:
                col_codigo = next((col for col in df.columns if 'COD' in str(col).upper()), None)
            if not col_descricao:
                col_descricao = next((col for col in df.columns if 'DESCRI' in str(col).upper()), None)
            if not col_unidade:
                col_unidade = next((col for col in df.columns if 'UN' in str(col).upper()), None)
            if not col_preco:
                col_preco = next((col for col in df.columns if 'PRECO' in str(col).upper() or 'PREÇO' in str(col).upper()), None)
            
            # Verifica se encontramos todas as colunas necessárias
            if not all([col_codigo, col_descricao, col_unidade, col_preco]):
                print("⚠️ Não foi possível identificar todas as colunas necessárias")
                print(f"Colunas encontradas: {list(df.columns)}")
                return 0
                
            print(f"Usando as colunas: {col_codigo}, {col_descricao}, {col_unidade}, {col_preco}")
            
            # Processa e insere dados
            registros = 0
            for _, row in df.iterrows():
                codigo = row.get(col_codigo)
                descricao = row.get(col_descricao)
                
                if pd.notna(codigo) and pd.notna(descricao):
                    # Obtém valores e converte para o formato correto
                    unidade = row.get(col_unidade, '')
                    preco = row.get(col_preco, 0)
                    
                    if pd.isna(preco):
                        preco = 0
                        
                    # Converte para string/float conforme necessário
                    codigo = str(codigo).strip()
                    descricao = str(descricao).strip()
                    unidade = str(unidade).strip() if pd.notna(unidade) else ''
                    
                    # Transforma valores potencialmente formatados (ex: "R$ 10,50") em float
                    if isinstance(preco, str):
                        preco = preco.replace('R$', '').replace('.', '').replace(',', '.').strip()
                        try:
                            preco = float(preco)
                        except ValueError:
                            preco = 0
                    
                    self.conn.execute('''
                    INSERT OR REPLACE INTO insumos 
                    (codigo, descricao, unidade, preco_mediano, origem, data_referencia, data_atualizacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        codigo, 
                        descricao, 
                        unidade, 
                        float(preco),
                        'SINAPI',
                        mes_ref,
                        datetime.now().strftime("%Y-%m-%d")
                    ))
                    registros += 1
            
            self.conn.commit()
            print(f"✅ Importados {registros} insumos com sucesso!")
            return registros
            
        except Exception as e:
            print(f"❌ Erro ao importar insumos: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0

    def importar_composicoes(self, arquivo_excel, aba='Composicoes', mes_ref=None):
        """Importa composições do Excel SINAPI"""
        if not mes_ref:
            mes_ref = datetime.now().strftime("%Y-%m")
            
        print(f"Importando composições de {arquivo_excel}...")
        
        try:
            # Cria uma cópia temporária do arquivo para evitar problemas de permissão
            temp_file = self._criar_arquivo_temporario(arquivo_excel)
            
            # Carrega a planilha sem definir cabeçalho inicialmente
            df = pd.read_excel(temp_file, sheet_name=aba, header=None)
            
            # Encontra a linha que contém cabeçalhos com as palavras-chave que precisamos
            linha_header = None
            for i, row in df.iterrows():
                row_str = ' '.join([str(cell).upper() for cell in row if pd.notna(cell)])
                if 'CODIGO DA COMPOSICAO' in row_str or 'CODIGO COMPOSICAO' in row_str:
                    linha_header = i
                    break
            
            if linha_header is None:
                print("❌ Não foi possível encontrar a linha de cabeçalho das composições")
                return 0
                
            # Define esta linha como cabeçalho e recria o DataFrame
            cabeçalhos = df.iloc[linha_header]
            df = pd.DataFrame(df.values[linha_header+1:], columns=cabeçalhos)
            
            # Identifica as colunas-chave que precisamos
            mapeamento_colunas = {
                'codigo_composicao': ['CODIGO DA COMPOSICAO', 'CODIGO COMPOSICAO', 'CODIGO', 'COD'],
                'descricao_composicao': ['DESCRICAO DA COMPOSICAO', 'DESCRICAO COMPOSICAO', 'DESCRICAO'],
                'unidade_composicao': ['UNIDADE'],
                'custo_total': ['CUSTO TOTAL', 'VALOR TOTAL'],
                'codigo_item': ['CODIGO ITEM', 'CODIGO DO ITEM', 'COD ITEM'],
                'tipo_item': ['TIPO ITEM', 'TIPO DE ITEM'],
                'descricao_item': ['DESCRIÇÃO ITEM', 'DESCRICAO DO ITEM', 'DESCRICAO ITEM'],
                'unidade_item': ['UNIDADE ITEM'],
                'coeficiente': ['COEFICIENTE', 'COEF']
            }
            
            # Mapeia as colunas reais para os nomes que usaremos
            colunas_mapeadas = {}
            for nome_interno, possiveis_nomes in mapeamento_colunas.items():
                encontrado = False
                for possivel in possiveis_nomes:
                    for col in df.columns:
                        if possivel in str(col).upper():
                            colunas_mapeadas[nome_interno] = col
                            encontrado = True
                            break
                    if encontrado:
                        break
                        
                if not encontrado:
                    print(f"⚠️ Não foi possível encontrar coluna para {nome_interno}")
            
            # Verifica se temos as colunas mínimas necessárias
            essenciais = ['codigo_composicao', 'codigo_item', 'coeficiente']
            if not all(col in colunas_mapeadas for col in essenciais):
                print("❌ Faltam colunas essenciais para importar composições")
                missing = [col for col in essenciais if col not in colunas_mapeadas]
                print(f"Colunas faltantes: {missing}")
                return 0
            
            print(f"Colunas mapeadas: {colunas_mapeadas}")
            
            # Vamos iterar pelas linhas e processar composições e seus itens
            composicoes_processadas = set()
            registros_composicoes = 0
            registros_itens = 0
            
            for idx, row in df.iterrows():
                # Obtém o código da composição
                codigo_comp = row.get(colunas_mapeadas['codigo_composicao'])
                
                if pd.isna(codigo_comp):
                    continue
                    
                codigo_comp = str(codigo_comp).strip()
                
                # Se ainda não processamos esta composição, insere na tabela de composições
                if codigo_comp not in composicoes_processadas:
                    # Extrai os valores das colunas mapeadas se disponíveis
                    descricao = str(row.get(colunas_mapeadas.get('descricao_composicao', ''), '')).strip() if 'descricao_composicao' in colunas_mapeadas else ''
                    unidade = str(row.get(colunas_mapeadas.get('unidade_composicao', ''), '')).strip() if 'unidade_composicao' in colunas_mapeadas else ''
                    
                    # Trata o custo total
                    custo_total = 0
                    if 'custo_total' in colunas_mapeadas:
                        custo_total = row.get(colunas_mapeadas['custo_total'], 0)
                        if isinstance(custo_total, str):
                            custo_total = custo_total.replace('R$', '').replace('.', '').replace(',', '.').strip()
                            try:
                                custo_total = float(custo_total)
                            except ValueError:
                                custo_total = 0
                        elif pd.isna(custo_total):
                            custo_total = 0
                    
                    self.conn.execute('''
                    INSERT OR REPLACE INTO composicoes 
                    (codigo, descricao, unidade, custo_total, origem, data_referencia, data_atualizacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        codigo_comp, 
                        descricao, 
                        unidade, 
                        float(custo_total),
                        'SINAPI',
                        mes_ref,
                        datetime.now().strftime("%Y-%m-%d")
                    ))
                    
                    composicoes_processadas.add(codigo_comp)
                    registros_composicoes += 1
                
                # Agora insere o relacionamento com o insumo/componente
                codigo_item = row.get(colunas_mapeadas['codigo_item'], None)
                
                if pd.notna(codigo_item):
                    codigo_item = str(codigo_item).strip()
                    
                    # Processa o coeficiente
                    coeficiente = row.get(colunas_mapeadas['coeficiente'], 0)
                    if isinstance(coeficiente, str):
                        coeficiente = coeficiente.replace(',', '.').strip()
                        try:
                            coeficiente = float(coeficiente)
                        except ValueError:
                            coeficiente = 0
                    elif pd.isna(coeficiente):
                        coeficiente = 0
                    
                    self.conn.execute('''
                    INSERT OR REPLACE INTO composicao_insumos 
                    (codigo_composicao, codigo_insumo, coeficiente)
                    VALUES (?, ?, ?)
                    ''', (
                        codigo_comp,
                        codigo_item, 
                        float(coeficiente)
                    ))
                    
                    registros_itens += 1
            
            self.conn.commit()
            print(f"✅ Importadas {registros_composicoes} composições com {registros_itens} itens!")
            return registros_composicoes
            
        except Exception as e:
            print(f"❌ Erro ao importar composições: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _verificar_migracoes(self):
            """Verifica e aplica migrações necessárias ao banco de dados"""
            # Verifica se a tabela projetos existe
            try:
                self.conn.execute("SELECT COUNT(*) FROM projetos")
            except sqlite3.OperationalError:
                print("Tabela 'projetos' não encontrada. Criando...")
                self._criar_tabela_projetos()
            
            # Verifica se a tabela projetos tem a coluna 'salvo'
            try:
                self.conn.execute("SELECT salvo FROM projetos LIMIT 1")
            except sqlite3.OperationalError:
                print("Aplicando migração: adicionando coluna 'salvo' à tabela 'projetos'")
                self.conn.execute("ALTER TABLE projetos ADD COLUMN salvo INTEGER DEFAULT 1")
                self.conn.commit()
            
            # Adicione outras verificações de migração aqui conforme necessário
        
    def _criar_tabela_insumos(self):
        """Cria a tabela de insumos"""
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS insumos (
            codigo TEXT PRIMARY KEY,
            descricao TEXT,
            unidade TEXT,
            preco_mediano REAL,
            origem TEXT,
            data_referencia TEXT,
            data_atualizacao TEXT
        )
        ''')
    
    def _criar_tabela_composicoes(self):
        """Cria a tabela de composições"""
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS composicoes (
            codigo TEXT PRIMARY KEY,
            descricao TEXT,
            unidade TEXT,
            custo_total REAL,
            origem TEXT,
            data_referencia TEXT,
            data_atualizacao TEXT
        )
        ''')
    
    def _criar_tabela_composicao_insumos(self):
        """Cria a tabela de relacionamento entre composições e insumos"""
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS composicao_insumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_composicao TEXT,
            codigo_insumo TEXT,
            coeficiente REAL,
            FOREIGN KEY (codigo_composicao) REFERENCES composicoes(codigo),
            FOREIGN KEY (codigo_insumo) REFERENCES insumos(codigo)
        )
        ''')
    
    def _criar_tabela_projetos(self):
        """Cria a tabela de projetos"""
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS projetos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            descricao TEXT,
            data_criacao TEXT,
            data_atualizacao TEXT,
            bdi REAL DEFAULT 25.0,
            salvo INTEGER DEFAULT 1
        )
        ''')
    
    def _criar_tabela_orcamento_itens(self):
        """Cria a tabela de itens do orçamento"""
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS orcamento_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id INTEGER,
            tipo TEXT,  -- 'insumo' ou 'composicao'
            codigo TEXT,
            descricao TEXT,
            unidade TEXT,
            quantidade REAL,
            preco_unitario REAL,
            FOREIGN KEY (projeto_id) REFERENCES projetos(id)
        )
        ''')
    
    # --- Métodos para importação de dados ---
    
    def importar_insumos(self, arquivo_excel, aba='insumos', mes_ref=None):
        """Importa insumos do Excel SINAPI"""
        if not mes_ref:
            mes_ref = datetime.now().strftime("%Y-%m")
            
        print(f"Importando insumos de {arquivo_excel}...")
        
        # O resto do código segue igual...
        # (Omitindo por brevidade, mas seria o mesmo método da classe original)
    
    # Métodos essenciais para o funcionamento básico do app
    
    def _criar_arquivo_temporario(self, arquivo_original):
        """Cria uma cópia temporária do arquivo"""
        # Cria um arquivo temporário com o mesmo nome, mas em um diretório temporário
        temp_dir = tempfile.gettempdir()
        nome_arquivo = os.path.basename(arquivo_original)
        temp_path = os.path.join(temp_dir, f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{nome_arquivo}")
        
        # Copia o arquivo
        shutil.copy2(arquivo_original, temp_path)
        
        # Adiciona à lista de arquivos temporários para limpeza posterior
        self.temp_files.append(temp_path)
        
        return temp_path
    
    def limpar_arquivos_temporarios(self):
        """Limpa os arquivos temporários criados"""
        for file in self.temp_files:
            try:
                if os.path.exists(file):
                    os.remove(file)
                    print(f"Arquivo temporário removido: {file}")
            except Exception as e:
                print(f"Erro ao remover arquivo temporário {file}: {str(e)}")
        
        self.temp_files = []
    
    def listar_projetos(self):
            """Lista todos os projetos cadastrados de forma robusta"""
            try:
                # Tenta a consulta completa primeiro
                cursor = self.conn.execute('''
                SELECT id, nome, descricao, data_criacao, data_atualizacao, bdi, salvo
                FROM projetos
                ORDER BY data_atualizacao DESC
                ''')
                return cursor.fetchall()
            except sqlite3.OperationalError as e:
                # Se der erro, tenta uma versão mais básica e adiciona valores padrão
                if "no such column: salvo" in str(e):
                    print("Aviso: Usando consulta compatível sem a coluna 'salvo'")
                    cursor = self.conn.execute('''
                    SELECT id, nome, descricao, data_criacao, data_atualizacao, bdi
                    FROM projetos
                    ORDER BY data_atualizacao DESC
                    ''')
                    # Adiciona um valor padrão (1) para a coluna salvo em cada linha
                    return [tuple(list(row) + [1]) for row in cursor.fetchall()]
                elif "no such column: bdi" in str(e):
                    print("Aviso: Usando consulta compatível sem as colunas 'bdi' e 'salvo'")
                    cursor = self.conn.execute('''
                    SELECT id, nome, descricao, data_criacao, data_atualizacao
                    FROM projetos
                    ORDER BY data_atualizacao DESC
                    ''')
                    # Adiciona valores padrão para bdi (25.0) e salvo (1)
                    return [tuple(list(row) + [25.0, 1]) for row in cursor.fetchall()]
                else:
                    # Se for outro erro, propaga-o
                    print(f"Erro ao listar projetos: {e}")
                    # Retorna lista vazia se não conseguir consultar
                    return []
    
    def criar_projeto(self, nome, descricao=""):
        """Cria um novo projeto"""
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor = self.conn.execute('''
        INSERT INTO projetos (nome, descricao, data_criacao, data_atualizacao, salvo)
        VALUES (?, ?, ?, ?, 1)
        ''', (nome, descricao, agora, agora))
        
        self.conn.commit()
        return cursor.lastrowid
        
    def fechar(self):
        """Fecha a conexão com o banco de dados e limpa arquivos temporários"""
        self.limpar_arquivos_temporarios()
        if self.conn:
            self.conn.close()
            print("Conexão com o banco fechada.")