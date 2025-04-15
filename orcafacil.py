import os
import sys
import pandas as pd
import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class SinapiImporter:
    def __init__(self, db_path='orcamento.db'):
        """Inicializa o importador SINAPI"""
        self.db_path = db_path
        self.conn = None
        self.setup_database()
        
    def setup_database(self):
        """Cria a conexão e as tabelas necessárias"""
        self.conn = sqlite3.connect(self.db_path)
        
        # Tabelas principais
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
        
        # Tabela de projetos
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS projetos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            descricao TEXT,
            data_criacao TEXT,
            data_atualizacao TEXT,
            bdi REAL DEFAULT 25.0
        )
        ''')
        
        # Tabela de itens do orçamento
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
        
        self.conn.commit()
    
    def importar_insumos(self, arquivo_excel, aba='insumos', mes_ref=None):
        """Importa insumos do Excel SINAPI"""
        if not mes_ref:
            mes_ref = datetime.now().strftime("%Y-%m")
            
        print(f"Importando insumos de {arquivo_excel}...")
        
        try:
            # Carrega a planilha sem definir cabeçalho inicialmente
            import shutil
            temp_file = "temp_sinapi_insumos.xlsx"
            shutil.copy2(arquivo_excel, temp_file)
            df = pd.read_excel(temp_file, sheet_name=aba, header=None)

            
            # Encontra a linha que contém 'CODIGO' para determinar onde os cabeçalhos reais estão
            linha_header = None
            for i, row in df.iterrows():
                if any(str(cell).strip().upper() == 'CODIGO' for cell in row if pd.notna(cell)):
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
            # Carrega a planilha sem definir cabeçalho inicialmente
            import shutil
            temp_file = "temp_sinapi_composicoes.xlsx"
            shutil.copy2(arquivo_excel, temp_file)
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
                'codigo_composicao': ['CODIGO DA COMPOSICAO', 'CODIGO COMPOSICAO'],
                'descricao_composicao': ['DESCRICAO DA COMPOSICAO', 'DESCRICAO COMPOSICAO'],
                'unidade_composicao': ['UNIDADE'],
                'custo_total': ['CUSTO TOTAL'],
                'codigo_item': ['CODIGO ITEM', 'CODIGO DO ITEM'],
                'tipo_item': ['TIPO ITEM', 'TIPO DE ITEM'],
                'descricao_item': ['DESCRIÇÃO ITEM', 'DESCRICAO DO ITEM'],
                'unidade_item': ['UNIDADE ITEM'],
                'coeficiente': ['COEFICIENTE']
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
            
    def pesquisar_insumos(self, termo):
        """Pesquisa insumos por termo na descrição ou código"""
        cursor = self.conn.execute('''
        SELECT codigo, descricao, unidade, preco_mediano, data_referencia 
        FROM insumos 
        WHERE descricao LIKE ? OR codigo LIKE ?
        ORDER BY descricao
        LIMIT 50
        ''', (f'%{termo}%', f'%{termo}%'))
        
        return cursor.fetchall()
    
    def pesquisar_composicoes(self, termo):
        """Pesquisa composições por termo na descrição ou código"""
        cursor = self.conn.execute('''
        SELECT codigo, descricao, unidade, custo_total, data_referencia 
        FROM composicoes 
        WHERE descricao LIKE ? OR codigo LIKE ?
        ORDER BY descricao
        LIMIT 50
        ''', (f'%{termo}%', f'%{termo}%'))
        
        return cursor.fetchall()
    
    def obter_insumo(self, codigo):
        """Obtém um insumo pelo código"""
        cursor = self.conn.execute('''
        SELECT codigo, descricao, unidade, preco_mediano 
        FROM insumos 
        WHERE codigo = ?
        ''', (codigo,))
        
        return cursor.fetchone()
    
    def obter_composicao(self, codigo):
        """Obtém uma composição pelo código"""
        cursor = self.conn.execute('''
        SELECT codigo, descricao, unidade, custo_total 
        FROM composicoes 
        WHERE codigo = ?
        ''', (codigo,))
        
        return cursor.fetchone()
    
    def obter_itens_composicao(self, codigo_composicao):
        """Obtém todos os itens de uma composição"""
        cursor = self.conn.execute('''
        SELECT 
            ci.codigo_insumo, 
            COALESCE(i.descricao, c.descricao) as descricao, 
            COALESCE(i.unidade, c.unidade) as unidade, 
            ci.coeficiente,
            COALESCE(i.preco_mediano, c.custo_total) as preco 
        FROM composicao_insumos ci
        LEFT JOIN insumos i ON ci.codigo_insumo = i.codigo
        LEFT JOIN composicoes c ON ci.codigo_insumo = c.codigo
        WHERE ci.codigo_composicao = ?
        ''', (codigo_composicao,))
        
        return cursor.fetchall()

    def criar_projeto(self, nome, descricao=""):
        """Cria um novo projeto"""
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor = self.conn.execute('''
        INSERT INTO projetos (nome, descricao, data_criacao, data_atualizacao)
        VALUES (?, ?, ?, ?)
        ''', (nome, descricao, agora, agora))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def listar_projetos(self):
        """Lista todos os projetos cadastrados"""
        cursor = self.conn.execute('''
        SELECT id, nome, descricao, data_criacao, data_atualizacao, bdi
        FROM projetos
        ORDER BY data_atualizacao DESC
        ''')
        
        return cursor.fetchall()
    
    def adicionar_item_orcamento(self, projeto_id, tipo, codigo, quantidade):
        """Adiciona um item ao orçamento"""
        if tipo == 'insumo':
            item = self.obter_insumo(codigo)
            if not item:
                raise ValueError(f"Insumo com código {codigo} não encontrado")
            preco = item[3]  # preco_mediano
        else:  # composicao
            item = self.obter_composicao(codigo)
            if not item:
                raise ValueError(f"Composição com código {codigo} não encontrada")
            preco = item[3]  # custo_total
        
        # Insere o item no orçamento
        self.conn.execute('''
        INSERT INTO orcamento_itens 
        (projeto_id, tipo, codigo, descricao, unidade, quantidade, preco_unitario)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            projeto_id,
            tipo,
            codigo,
            item[1],  # descricao
            item[2],  # unidade
            quantidade,
            preco
        ))
        
        # Atualiza data do projeto
        self.conn.execute('''
        UPDATE projetos SET data_atualizacao = ? WHERE id = ?
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), projeto_id))
        
        self.conn.commit()
    
    def obter_itens_orcamento(self, projeto_id):
        """Obtém todos os itens de um orçamento"""
        cursor = self.conn.execute('''
        SELECT id, tipo, codigo, descricao, unidade, quantidade, preco_unitario
        FROM orcamento_itens
        WHERE projeto_id = ?
        ORDER BY id
        ''', (projeto_id,))
        
        return cursor.fetchall()
    
    def calcular_total_orcamento(self, projeto_id):
        """Calcula o total do orçamento"""
        cursor = self.conn.execute('''
        SELECT COALESCE(SUM(quantidade * preco_unitario), 0) as total
        FROM orcamento_itens
        WHERE projeto_id = ?
        ''', (projeto_id,))
        
        return cursor.fetchone()[0]
    
    def exportar_orcamento_excel(self, projeto_id, caminho_arquivo):
        """Exporta o orçamento para Excel"""
        # Obtém informações do projeto
        cursor = self.conn.execute('''
        SELECT nome, descricao, bdi FROM projetos WHERE id = ?
        ''', (projeto_id,))
        projeto = cursor.fetchone()
        
        if not projeto:
            raise ValueError(f"Projeto com ID {projeto_id} não encontrado")
        
        nome_projeto, descricao_projeto, bdi = projeto
        
        # Obtém os itens do orçamento
        itens = self.obter_itens_orcamento(projeto_id)
        
        # Prepara os dados para o Excel
        dados = []
        for item in itens:
            id_item, tipo, codigo, descricao, unidade, quantidade, preco_unitario = item
            valor_sem_bdi = quantidade * preco_unitario
            valor_com_bdi = valor_sem_bdi * (1 + bdi/100)
            
            dados.append({
                'Item': id_item,
                'Tipo': 'Insumo' if tipo == 'insumo' else 'Composição',
                'Código': codigo,
                'Descrição': descricao,
                'Unidade': unidade,
                'Quantidade': quantidade,
                'Preço Unitário': preco_unitario,
                'Valor Total': valor_sem_bdi,
                f'Valor com BDI ({bdi}%)': valor_com_bdi
            })
        
        # Cria o DataFrame
        df = pd.DataFrame(dados)
        
        # Cria o Excel
        with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
            # Primeira aba - Resumo
            total_sem_bdi = sum(d['Valor Total'] for d in dados)
            total_com_bdi = sum(d[f'Valor com BDI ({bdi}%)'] for d in dados)
            
            resumo = pd.DataFrame([
                {'Item': 'Nome do Projeto', 'Valor': nome_projeto},
                {'Item': 'Descrição', 'Valor': descricao_projeto},
                {'Item': 'Data', 'Valor': datetime.now().strftime("%d/%m/%Y")},
                {'Item': 'BDI', 'Valor': f"{bdi}%"},
                {'Item': 'Total sem BDI', 'Valor': f"R$ {total_sem_bdi:.2f}"},
                {'Item': 'Total com BDI', 'Valor': f"R$ {total_com_bdi:.2f}"}
            ])
            
            resumo.to_excel(writer, sheet_name='Resumo', index=False)
            
            # Segunda aba - Orçamento Detalhado
            df.to_excel(writer, sheet_name='Orçamento Detalhado', index=False)
        
        return caminho_arquivo
    
    def fechar(self):
        """Fecha a conexão com o banco de dados"""
        if self.conn:
            self.conn.close()


class OrcamentoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OrçaFácil - Sistema de Orçamento para Obras")
        self.root.geometry("1200x700")
        
        # Inicializa o banco de dados
        self.db = SinapiImporter()
        
        # Variáveis
        self.projeto_atual = None
        self.termo_pesquisa = tk.StringVar()
        self.tipo_pesquisa = tk.StringVar(value="insumo")
        self.quantidade = tk.DoubleVar(value=1.0)
        
        # Configuração da interface
        self.create_menu()
        self.create_widgets()
        
        # Atualiza a lista de projetos
        self.atualizar_lista_projetos()
    
    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        # Menu Arquivo
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Novo Projeto", command=self.novo_projeto)
        filemenu.add_command(label="Abrir Projeto", command=self.abrir_projeto)
        filemenu.add_separator()
        filemenu.add_command(label="Importar SINAPI", command=self.importar_sinapi)
        filemenu.add_separator()
        filemenu.add_command(label="Exportar para Excel", command=self.exportar_excel)
        filemenu.add_separator()
        filemenu.add_command(label="Sair", command=self.root.quit)
        menubar.add_cascade(label="Arquivo", menu=filemenu)
        
        # Menu Ferramentas
        toolsmenu = tk.Menu(menubar, tearoff=0)
        toolsmenu.add_command(label="Calcular BDI", command=self.calcular_bdi)
        menubar.add_cascade(label="Ferramentas", menu=toolsmenu)
        
        # Menu Ajuda
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Sobre", command=self.sobre)
        menubar.add_cascade(label="Ajuda", menu=helpmenu)
        
        self.root.config(menu=menubar)
    
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame superior - Informações do projeto
        proj_frame = ttk.LabelFrame(main_frame, text="Projeto", padding=5)
        proj_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(proj_frame, text="Projeto atual:").grid(row=0, column=0, sticky=tk.W)
        self.lbl_projeto = ttk.Label(proj_frame, text="Nenhum projeto selecionado")
        self.lbl_projeto.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(proj_frame, text="Total:").grid(row=0, column=2, sticky=tk.W, padx=(20,0))
        self.lbl_total = ttk.Label(proj_frame, text="R$ 0,00")
        self.lbl_total.grid(row=0, column=3, sticky=tk.W)
        
        ttk.Label(proj_frame, text="BDI:").grid(row=0, column=4, sticky=tk.W, padx=(20,0))
        self.lbl_bdi = ttk.Label(proj_frame, text="25%")
        self.lbl_bdi.grid(row=0, column=5, sticky=tk.W)
        
        ttk.Label(proj_frame, text="Total com BDI:").grid(row=0, column=6, sticky=tk.W, padx=(20,0))
        self.lbl_total_bdi = ttk.Label(proj_frame, text="R$ 0,00")
        self.lbl_total_bdi.grid(row=0, column=7, sticky=tk.W)
        
        # Frame do meio - dividido em dois painéis
        mid_frame = ttk.Frame(main_frame)
        mid_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Painel esquerdo - Pesquisa e adição de itens
        left_frame = ttk.LabelFrame(mid_frame, text="Adicionar Itens", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))
        
        # Frame de pesquisa
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(search_frame, text="Pesquisar:").pack(side=tk.LEFT)
        ttk.Entry(search_frame, textvariable=self.termo_pesquisa, width=30).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(search_frame, text="Insumo", variable=self.tipo_pesquisa, value="insumo").pack(side=tk.LEFT)
        ttk.Radiobutton(search_frame, text="Composição", variable=self.tipo_pesquisa, value="composicao").pack(side=tk.LEFT)
        
        ttk.Button(search_frame, text="Pesquisar", command=self.pesquisar).pack(side=tk.LEFT, padx=5)
        
        # Lista de resultados
        result_frame = ttk.Frame(left_frame)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.tree_resultados = ttk.Treeview(result_frame, columns=("codigo", "descricao", "unidade", "preco"))
        self.tree_resultados.heading("#0", text="")
        self.tree_resultados.heading("codigo", text="Código")
        self.tree_resultados.heading("descricao", text="Descrição")
        self.tree_resultados.heading("unidade", text="Unidade")
        self.tree_resultados.heading("preco", text="Preço")
        
        self.tree_resultados.column("#0", width=0, stretch=tk.NO)
        self.tree_resultados.column("codigo", width=100)
        self.tree_resultados.column("descricao", width=400)
        self.tree_resultados.column("unidade", width=80)
        self.tree_resultados.column("preco", width=100)
        
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.tree_resultados.yview)
        self.tree_resultados.configure(yscrollcommand=scrollbar.set)
        
        self.tree_resultados.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Frame para adicionar item ao orçamento
        add_frame = ttk.Frame(left_frame)
        add_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(add_frame, text="Quantidade:").pack(side=tk.LEFT)
        ttk.Entry(add_frame, textvariable=self.quantidade, width=10).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(add_frame, text="Adicionar ao Orçamento", command=self.adicionar_ao_orcamento).pack(side=tk.LEFT, padx=5)
        
        # Painel direito - Orçamento atual
        right_frame = ttk.LabelFrame(mid_frame, text="Orçamento Atual", padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Lista de itens do orçamento
        self.tree_orcamento = ttk.Treeview(right_frame, columns=("id", "tipo", "codigo", "descricao", "unidade", "qtd", "preco", "total"))
        self.tree_orcamento.heading("#0", text="")
        self.tree_orcamento.heading("id", text="#")
        self.tree_orcamento.heading("tipo", text="Tipo")
        self.tree_orcamento.heading("codigo", text="Código")
        self.tree_orcamento.heading("descricao", text="Descrição")
        self.tree_orcamento.heading("unidade", text="Un")
        self.tree_orcamento.heading("qtd", text="Qtd")
        self.tree_orcamento.heading("preco", text="Preço Un")
        self.tree_orcamento.heading("total", text="Total")
        
        self.tree_orcamento.column("#0", width=0, stretch=tk.NO)
        self.tree_orcamento.column("id", width=40)
        self.tree_orcamento.column("tipo", width=80)
        self.tree_orcamento.column("codigo", width=80)
        self.tree_orcamento.column("descricao", width=300)
        self.tree_orcamento.column("unidade", width=50)
        self.tree_orcamento.column("qtd", width=80)
        self.tree_orcamento.column("preco", width=80)
        self.tree_orcamento.column("total", width=80)
        
        scrollbar2 = ttk.Scrollbar(right_frame, orient="vertical", command=self.tree_orcamento.yview)
        self.tree_orcamento.configure(yscrollcommand=scrollbar2.set)
        
        self.tree_orcamento.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botões de ação para orçamento
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(action_frame, text="Remover Item", command=self.remover_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Editar Quantidade", command=self.editar_quantidade).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Ver Composição", command=self.ver_composicao).pack(side=tk.LEFT, padx=5)
        
        # Frame inferior - Status e controles
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(bottom_frame, text="Status:").pack(side=tk.LEFT)
        self.lbl_status = ttk.Label(bottom_frame, text="Pronto")
        self.lbl_status.pack(side=tk.LEFT, padx=5)
    
    def atualizar_lista_projetos(self):
        """Atualiza a lista de projetos disponíveis"""
        self.projetos = self.db.listar_projetos()
    
    def novo_projeto(self):
        """Cria um novo projeto"""
        # Janela de diálogo para criar um novo projeto
        dialog = tk.Toplevel(self.root)
        dialog.title("Novo Projeto")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Nome do Projeto:").pack(pady=(20, 5))
        nome_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=nome_var, width=40).pack(pady=5)
        
        ttk.Label(dialog, text="Descrição:").pack(pady=5)
        desc_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=desc_var, width=40).pack(pady=5)
        
        def criar():
            nome = nome_var.get().strip()
            if not nome:
                messagebox.showerror("Erro", "O nome do projeto é obrigatório")
                return
            
            # Cria o projeto no banco
            projeto_id = self.db.criar_projeto(nome, desc_var.get())
            
            # Atualiza a interface
            self.atualizar_lista_projetos()
            self.projeto_atual = projeto_id
            self.atualizar_interface()
            
            # Fecha o diálogo
            dialog.destroy()
        
        ttk.Button(dialog, text="Criar", command=criar).pack(pady=20)
    
    def abrir_projeto(self):
        """Abre um projeto existente"""
        # Janela de diálogo para selecionar um projeto
        dialog = tk.Toplevel(self.root)
        dialog.title("Abrir Projeto")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Lista de projetos
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Selecione um projeto:").pack(pady=5)
        
        # TreeView para listar os projetos
        tree = ttk.Treeview(frame, columns=("id", "nome", "descricao", "data"))
        tree.heading("#0", text="")
        tree.heading("id", text="ID")
        tree.heading("nome", text="Nome")
        tree.heading("descricao", text="Descrição")
        tree.heading("data", text="Última Atualização")
        
        tree.column("#0", width=0, stretch=tk.NO)
        tree.column("id", width=50)
        tree.column("nome", width=150)
        tree.column("descricao", width=200)
        tree.column("data", width=150)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Preenche a lista de projetos
        for projeto in self.projetos:
            tree.insert("", tk.END, values=(projeto[0], projeto[1], projeto[2], projeto[4]))
        
        def abrir():
            selecao = tree.selection()
            if not selecao:
                messagebox.showerror("Erro", "Selecione um projeto")
                return
            
            # Obtém o ID do projeto selecionado
            item = tree.item(selecao[0])
            projeto_id = item['values'][0]
            
            # Atualiza a interface
            self.projeto_atual = projeto_id
            self.atualizar_interface()
            
            # Fecha o diálogo
            dialog.destroy()
        
        ttk.Button(dialog, text="Abrir", command=abrir).pack(pady=10)
    
    def importar_sinapi(self):
        """Importa dados do SINAPI"""
        # Janela de diálogo para importar dados
        dialog = tk.Toplevel(self.root)
        dialog.title("Importar SINAPI")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Variáveis
        arquivo_var = tk.StringVar()
        mes_ref_var = tk.StringVar(value=datetime.now().strftime("%Y-%m"))
        
        # Widgets
        ttk.Label(frame, text="Arquivo Excel SINAPI:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=arquivo_var, width=40).grid(row=0, column=1, sticky=tk.W, pady=5)
        ttk.Button(frame, text="...", command=lambda: arquivo_var.set(filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx;*.xls")]))).grid(row=0, column=2, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="Mês de Referência (YYYY-MM):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=mes_ref_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="Dados a importar:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        importar_insumos_var = tk.BooleanVar(value=True)
        importar_comp_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(frame, text="Insumos", variable=importar_insumos_var).grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(frame, text="Composições", variable=importar_comp_var).grid(row=4, column=0, sticky=tk.W, pady=2)
        
        # Lista de status da importação
        status_text = tk.Text(frame, height=8, width=50, wrap=tk.WORD)
        status_text.grid(row=5, column=0, columnspan=3, pady=10)
        
        def importar():
            arquivo = arquivo_var.get().strip()
            if not arquivo or not os.path.exists(arquivo):
                messagebox.showerror("Erro", "Arquivo não encontrado")
                return
            
            mes_ref = mes_ref_var.get().strip()
            
            # Atualiza o status
            status_text.delete(1.0, tk.END)
            status_text.insert(tk.END, f"Iniciando importação...\n")
            dialog.update()
            
            try:
                # Importa insumos
                if importar_insumos_var.get():
                    status_text.insert(tk.END, "Importando insumos...\n")
                    dialog.update()
                    
                    # Tenta importar da aba padrão e alternativas
                    try:
                        total = self.db.importar_insumos(arquivo, aba='insumos', mes_ref=mes_ref)
                    except Exception as e:
                        status_text.insert(tk.END, f"Erro na aba 'insumos': {str(e)}\nTentando 'Insumos'...\n")
                        dialog.update()
                        try:
                            total = self.db.importar_insumos(arquivo, aba='Insumos', mes_ref=mes_ref)
                        except Exception as e:
                            status_text.insert(tk.END, f"Erro na aba 'Insumos': {str(e)}\n")
                            dialog.update()
                            total = 0
                    
                    status_text.insert(tk.END, f"Importados {total} insumos\n")
                    dialog.update()
                
                # Importa composições
                if importar_comp_var.get():
                    status_text.insert(tk.END, "Importando composições...\n")
                    dialog.update()
                    
                    # Tenta importar da aba padrão e alternativas
                    try:
                        total = self.db.importar_composicoes(arquivo, aba='Composicoes', mes_ref=mes_ref)
                    except Exception as e:
                        status_text.insert(tk.END, f"Erro na aba 'Composicoes': {str(e)}\nTentando 'composicoes'...\n")
                        dialog.update()
                        try:
                            total = self.db.importar_composicoes(arquivo, aba='composicoes', mes_ref=mes_ref)
                        except Exception as e:
                            status_text.insert(tk.END, f"Erro na aba 'composicoes': {str(e)}\n")
                            dialog.update()
                            total = 0
                    
                    status_text.insert(tk.END, f"Importadas {total} composições\n")
                    dialog.update()
                
                status_text.insert(tk.END, "Importação concluída!")
                
            except Exception as e:
                status_text.insert(tk.END, f"Erro: {str(e)}")
        
        ttk.Button(frame, text="Importar", command=importar).grid(row=6, column=0, pady=10)
        ttk.Button(frame, text="Fechar", command=dialog.destroy).grid(row=6, column=1, pady=10)
    
    def atualizar_interface(self):
        """Atualiza a interface com os dados do projeto atual"""
        if self.projeto_atual is None:
            self.lbl_projeto.config(text="Nenhum projeto selecionado")
            self.lbl_total.config(text="R$ 0,00")
            self.lbl_bdi.config(text="25%")
            self.lbl_total_bdi.config(text="R$ 0,00")
            self.tree_orcamento.delete(*self.tree_orcamento.get_children())
            return
        
        # Obtém informações do projeto
        for projeto in self.projetos:
            if projeto[0] == self.projeto_atual:
                self.lbl_projeto.config(text=projeto[1])
                self.lbl_bdi.config(text=f"{projeto[5]}%")
                break
        
        # Obtém itens do orçamento
        self.tree_orcamento.delete(*self.tree_orcamento.get_children())
        itens = self.db.obter_itens_orcamento(self.projeto_atual)
        
        for item in itens:
            id_item, tipo, codigo, descricao, unidade, quantidade, preco = item
            total = quantidade * preco
            tipo_label = "Insumo" if tipo == "insumo" else "Composição"
            
            self.tree_orcamento.insert("", tk.END, values=(
                id_item, tipo_label, codigo, descricao, unidade, 
                f"{quantidade:.2f}", f"R$ {preco:.2f}", f"R$ {total:.2f}"
            ))
        
        # Calcula total
        total = self.db.calcular_total_orcamento(self.projeto_atual)
        self.lbl_total.config(text=f"R$ {total:.2f}")
        
        # Calcula total com BDI
        bdi = None
        for projeto in self.projetos:
            if projeto[0] == self.projeto_atual:
                bdi = projeto[5]
                break
        
        if bdi is not None:
            total_bdi = total * (1 + bdi/100)
            self.lbl_total_bdi.config(text=f"R$ {total_bdi:.2f}")
    
    def pesquisar(self):
        """Pesquisa insumos ou composições"""
        termo = self.termo_pesquisa.get().strip()
        tipo = self.tipo_pesquisa.get()
        
        if not termo:
            messagebox.showinfo("Aviso", "Digite um termo para pesquisar")
            return
        
        # Limpa resultados anteriores
        self.tree_resultados.delete(*self.tree_resultados.get_children())
        
        try:
            if tipo == "insumo":
                resultados = self.db.pesquisar_insumos(termo)
                
                for res in resultados:
                    codigo, descricao, unidade, preco, data_ref = res
                    self.tree_resultados.insert("", tk.END, values=(
                        codigo, descricao, unidade, f"R$ {preco:.2f}"
                    ))
            else:
                resultados = self.db.pesquisar_composicoes(termo)
                
                for res in resultados:
                    codigo, descricao, unidade, preco, data_ref = res
                    self.tree_resultados.insert("", tk.END, values=(
                        codigo, descricao, unidade, f"R$ {preco:.2f}"
                    ))
            
            self.lbl_status.config(text=f"Encontrados {len(resultados)} resultados")
        
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao pesquisar: {str(e)}")
    
    def adicionar_ao_orcamento(self):
        """Adiciona o item selecionado ao orçamento"""
        if self.projeto_atual is None:
            messagebox.showinfo("Aviso", "Selecione ou crie um projeto primeiro")
            return
        
        selecao = self.tree_resultados.selection()
        if not selecao:
            messagebox.showinfo("Aviso", "Selecione um item para adicionar")
            return
        
        # Obtém os dados do item selecionado
        item = self.tree_resultados.item(selecao[0])
        codigo = item['values'][0]
        tipo = self.tipo_pesquisa.get()
        quantidade = self.quantidade.get()
        
        try:
            self.db.adicionar_item_orcamento(self.projeto_atual, tipo, codigo, quantidade)
            self.atualizar_interface()
            self.lbl_status.config(text=f"Item adicionado ao orçamento")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao adicionar item: {str(e)}")
    
    def remover_item(self):
        """Remove o item selecionado do orçamento"""
        if self.projeto_atual is None:
            return
        
        selecao = self.tree_orcamento.selection()
        if not selecao:
            messagebox.showinfo("Aviso", "Selecione um item para remover")
            return
        
        item = self.tree_orcamento.item(selecao[0])
        id_item = item['values'][0]
        
        if messagebox.askyesno("Confirmar", "Deseja realmente remover este item?"):
            try:
                self.db.conn.execute("DELETE FROM orcamento_itens WHERE id = ?", (id_item,))
                self.db.conn.commit()
                self.atualizar_interface()
                self.lbl_status.config(text="Item removido")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao remover item: {str(e)}")
    
    def editar_quantidade(self):
        """Edita a quantidade do item selecionado"""
        if self.projeto_atual is None:
            return
        
        selecao = self.tree_orcamento.selection()
        if not selecao:
            messagebox.showinfo("Aviso", "Selecione um item para editar")
            return
        
        item = self.tree_orcamento.item(selecao[0])
        id_item = item['values'][0]
        qtd_atual = float(item['values'][5])
        
        # Janela de diálogo para editar a quantidade
        dialog = tk.Toplevel(self.root)
        dialog.title("Editar Quantidade")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Nova quantidade:").pack(pady=(20, 5))
        qtd_var = tk.DoubleVar(value=qtd_atual)
        ttk.Entry(dialog, textvariable=qtd_var, width=20).pack(pady=5)
        
        def atualizar():
            nova_qtd = qtd_var.get()
            
            try:
                self.db.conn.execute(
                    "UPDATE orcamento_itens SET quantidade = ? WHERE id = ?", 
                    (nova_qtd, id_item)
                )
                self.db.conn.commit()
                self.atualizar_interface()
                self.lbl_status.config(text="Quantidade atualizada")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao atualizar quantidade: {str(e)}")
        
        ttk.Button(dialog, text="Atualizar", command=atualizar).pack(pady=20)
    
    def ver_composicao(self):
        """Mostra os detalhes de uma composição"""
        selecao = self.tree_orcamento.selection()
        if not selecao:
            # Verifica se há seleção na árvore de resultados
            selecao = self.tree_resultados.selection()
            if not selecao:
                messagebox.showinfo("Aviso", "Selecione uma composição para visualizar")
                return
            
            item = self.tree_resultados.item(selecao[0])
            tipo = self.tipo_pesquisa.get()
            if tipo != "composicao":
                messagebox.showinfo("Aviso", "Item selecionado não é uma composição")
                return
            
            codigo = item['values'][0]
        else:
            item = self.tree_orcamento.item(selecao[0])
            tipo = item['values'][1]
            if tipo != "Composição":
                messagebox.showinfo("Aviso", "Item selecionado não é uma composição")
                return
            
            codigo = item['values'][2]
        
        # Obtém os itens da composição
        try:
            itens = self.db.obter_itens_composicao(codigo)
            
            # Cria uma janela para mostrar os detalhes
            dialog = tk.Toplevel(self.root)
            dialog.title(f"Composição {codigo}")
            dialog.geometry("700x400")
            dialog.transient(self.root)
            
            frame = ttk.Frame(dialog, padding=10)
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Obtém dados da composição
            comp = self.db.obter_composicao(codigo)
            if comp:
                ttk.Label(frame, text=f"Composição: {comp[1]}").pack(anchor=tk.W)
                ttk.Label(frame, text=f"Unidade: {comp[2]}").pack(anchor=tk.W)
                ttk.Label(frame, text=f"Custo Total: R$ {comp[3]:.2f}").pack(anchor=tk.W)
            
            # TreeView para listar os itens
            tree = ttk.Treeview(frame, columns=("codigo", "descricao", "unidade", "coef", "preco", "total"))
            tree.heading("#0", text="")
            tree.heading("codigo", text="Código")
            tree.heading("descricao", text="Descrição")
            tree.heading("unidade", text="Un")
            tree.heading("coef", text="Coef")
            tree.heading("preco", text="Preço Un")
            tree.heading("total", text="Total")
            
            tree.column("#0", width=0, stretch=tk.NO)
            tree.column("codigo", width=80)
            tree.column("descricao", width=250)
            tree.column("unidade", width=50)
            tree.column("coef", width=80)
            tree.column("preco", width=80)
            tree.column("total", width=80)
            
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Preenche a lista de itens
            total_comp = 0
            for item in itens:
                codigo_item, descricao, unidade, coef, preco = item
                total = coef * preco if preco else 0
                total_comp += total
                
                tree.insert("", tk.END, values=(
                    codigo_item, descricao, unidade, 
                    f"{coef:.4f}", f"R$ {preco:.2f}", f"R$ {total:.2f}"
                ))
            
            ttk.Label(frame, text=f"Total calculado: R$ {total_comp:.2f}").pack(anchor=tk.E, pady=5)
            ttk.Button(frame, text="Fechar", command=dialog.destroy).pack(pady=10)
        
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar composição: {str(e)}")
    
    def exportar_excel(self):
        """Exporta o orçamento para Excel"""
        if self.projeto_atual is None:
            messagebox.showinfo("Aviso", "Selecione ou crie um projeto primeiro")
            return
        
        # Solicita o caminho para salvar o arquivo
        caminho = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        
        if not caminho:
            return
        
        try:
            self.db.exportar_orcamento_excel(self.projeto_atual, caminho)
            messagebox.showinfo("Sucesso", f"Orçamento exportado para {caminho}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar: {str(e)}")
    
    def calcular_bdi(self):
        """Abre a calculadora de BDI"""
        if self.projeto_atual is None:
            messagebox.showinfo("Aviso", "Selecione ou crie um projeto primeiro")
            return
        
        # Janela de diálogo para calcular BDI
        dialog = tk.Toplevel(self.root)
        dialog.title("Calculadora de BDI")
        dialog.geometry("400x450")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Obtém o BDI atual do projeto
        bdi_atual = None
        for projeto in self.projetos:
            if projeto[0] == self.projeto_atual:
                bdi_atual = projeto[5]
                break
        
        ttk.Label(frame, text="Calculadora de BDI", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 10)
        )
        
        # Componentes do BDI
        ttk.Label(frame, text="Administração Central (%):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ac_var = tk.DoubleVar(value=4.0)
        ttk.Entry(frame, textvariable=ac_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="Seguro e Garantia (%):").grid(row=2, column=0, sticky=tk.W, pady=5)
        sg_var = tk.DoubleVar(value=0.8)
        ttk.Entry(frame, textvariable=sg_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="Risco (%):").grid(row=3, column=0, sticky=tk.W, pady=5)
        r_var = tk.DoubleVar(value=1.2)
        ttk.Entry(frame, textvariable=r_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="Despesas Financeiras (%):").grid(row=4, column=0, sticky=tk.W, pady=5)
        df_var = tk.DoubleVar(value=1.0)
        ttk.Entry(frame, textvariable=df_var, width=10).grid(row=4, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="Lucro (%):").grid(row=5, column=0, sticky=tk.W, pady=5)
        l_var = tk.DoubleVar(value=7.0)
        ttk.Entry(frame, textvariable=l_var, width=10).grid(row=5, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="Tributos - PIS+COFINS+ISS (%):").grid(row=6, column=0, sticky=tk.W, pady=5)
        t_var = tk.DoubleVar(value=5.65)
        ttk.Entry(frame, textvariable=t_var, width=10).grid(row=6, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="CPRB (%):").grid(row=7, column=0, sticky=tk.W, pady=5)
        cprb_var = tk.DoubleVar(value=4.5)
        ttk.Entry(frame, textvariable=cprb_var, width=10).grid(row=7, column=1, sticky=tk.W, pady=5)
        
        # Manual input
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=8, column=0, columnspan=2, sticky="ew", pady=10)
        
        ttk.Label(frame, text="OU insira o BDI manualmente:").grid(row=9, column=0, sticky=tk.W, pady=5)
        bdi_man_var = tk.DoubleVar(value=bdi_atual if bdi_atual else 25.0)
        ttk.Entry(frame, textvariable=bdi_man_var, width=10).grid(row=9, column=1, sticky=tk.W, pady=5)
        
        # Resultado
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=10, column=0, columnspan=2, sticky="ew", pady=10)
        
        ttk.Label(frame, text="BDI Calculado (%):").grid(row=11, column=0, sticky=tk.W, pady=5)
        resultado_var = tk.StringVar(value="---")
        ttk.Label(frame, textvariable=resultado_var, font=("Arial", 10, "bold")).grid(
            row=11, column=1, sticky=tk.W, pady=5
        )
        
        def calcular():
            # Fórmula do BDI conforme Acórdão TCU
            ac = ac_var.get() / 100
            sg = sg_var.get() / 100
            r = r_var.get() / 100
            df = df_var.get() / 100
            l = l_var.get() / 100
            t = t_var.get() / 100
            cprb = cprb_var.get() / 100
            
            numerador = (1 + ac + sg + r + df) * (1 + l)
            denominador = 1 - (t + cprb)
            
            bdi = (numerador / denominador - 1) * 100
            resultado_var.set(f"{bdi:.2f}%")
        
        def aplicar():
            # Obtém o BDI (calculado ou manual)
            if resultado_var.get() != "---":
                bdi = float(resultado_var.get().replace("%", ""))
            else:
                bdi = bdi_man_var.get()
            
            # Atualiza o BDI do projeto
            try:
                self.db.conn.execute(
                    "UPDATE projetos SET bdi = ? WHERE id = ?", 
                    (bdi, self.projeto_atual)
                )
                self.db.conn.commit()
                self.atualizar_lista_projetos()
                self.atualizar_interface()
                messagebox.showinfo("Sucesso", f"BDI atualizado para {bdi:.2f}%")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao atualizar BDI: {str(e)}")
        
        ttk.Button(frame, text="Calcular", command=calcular).grid(row=12, column=0, pady=15)
        ttk.Button(frame, text="Aplicar", command=aplicar).grid(row=12, column=1, pady=15)
    
    def sobre(self):
        """Mostra informações sobre o sistema"""
        messagebox.showinfo(
            "Sobre",
            "OrçaFácil - Sistema de Orçamento para Obras\n\n"
            "Versão 1.0\n\n"
            "Desenvolvido como demonstração."
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = OrcamentoApp(root)
    root.mainloop()