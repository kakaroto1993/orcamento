#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Diálogos e janelas secundárias para o OrçaFácil
"""

import os
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime
import pandas as pd

# Importações internas
from ui.components import ScrollableTreeView


class DialogBase(tk.Toplevel):
    """Classe base para diálogos"""
    
    def __init__(self, parent, title, size=(400, 300)):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{size[0]}x{size[1]}")
        self.transient(parent)
        self.grab_set()
        
        # Centraliza o diálogo
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # Conteúdo principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Resultado final (será definido pelas subclasses)
        self.resultado = None
        
        # Configura para fechar com Escape
        self.bind("<Escape>", lambda e: self.destroy())


class NovoProjeto(DialogBase):
    """Diálogo para criar um novo projeto"""
    
    def __init__(self, parent, db):
        super().__init__(parent, "Novo Projeto", (500, 250))
        self.db = db
        self.nome_projeto = ""
        
        # Elementos do diálogo
        ctk.CTkLabel(self.main_frame, text="Nome do Projeto:", 
                   font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.nome_var = tk.StringVar()
        ctk.CTkEntry(self.main_frame, textvariable=self.nome_var, width=400).pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(self.main_frame, text="Descrição:", 
                   font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.desc_var = tk.StringVar()
        ctk.CTkEntry(self.main_frame, textvariable=self.desc_var, width=400).pack(fill="x", pady=(0, 20))
        
        # Botões
        btn_frame = ctk.CTkFrame(self.main_frame)
        btn_frame.pack(fill="x", pady=(20, 0))
        
        ctk.CTkButton(btn_frame, text="Cancelar", command=self.destroy).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Criar", command=self._criar_projeto).pack(side="right", padx=5)
    
    def _criar_projeto(self):
            """Cria um novo projeto no banco de dados"""
            nome = self.nome_var.get().strip()
            if not nome:
                messagebox.showerror("Erro", "O nome do projeto é obrigatório")
                return
            
            try:
                # Cria o projeto no banco
                projeto_id = self.db.criar_projeto(nome, self.desc_var.get())
                
                # Define o resultado e nome para o chamador
                self.resultado = projeto_id
                self.nome_projeto = nome
                
                # Fecha o diálogo
                self.destroy()
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível criar o projeto: {str(e)}")
                print(f"Erro ao criar projeto: {e}")


class AbrirProjeto(DialogBase):
    """Diálogo para abrir um projeto existente"""
    
    def __init__(self, parent, db, projetos):
        super().__init__(parent, "Abrir Projeto", (700, 500))
        self.db = db
        self.projetos = projetos
        self.nome_projeto = ""
        
        # Conteúdo
        ctk.CTkLabel(self.main_frame, text="Selecione um projeto:", 
                   font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        # Usa o TreeView customizado
        proj_frame = ctk.CTkFrame(self.main_frame)
        proj_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        self.tree = ScrollableTreeView(
            proj_frame,
            columns=("id", "nome", "descricao", "data", "salvo"),
            headings=["ID", "Nome", "Descrição", "Última Atualização", "Status"],
            column_widths=[40, 150, 250, 150, 60]
        )
        self.tree.pack(fill="both", expand=True)
        
        # Preenche a lista de projetos
        for projeto in self.projetos:
            salvo = "Salvo" if projeto[6] == 1 else "Não Salvo"
            self.tree.insert("", "end", values=(projeto[0], projeto[1], projeto[2], projeto[4], salvo))
        
        # Botões
        btn_frame = ctk.CTkFrame(self.main_frame)
        btn_frame.pack(fill="x")
        
        ctk.CTkButton(btn_frame, text="Cancelar", command=self.destroy).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Abrir", command=self._abrir_projeto).pack(side="right", padx=5)
    
    def _abrir_projeto(self):
        """Abre o projeto selecionado"""
        selecao = self.tree.selection()
        if not selecao:
            messagebox.showerror("Erro", "Selecione um projeto")
            return
        
        # Obtém o ID do projeto selecionado
        item = self.tree.item(selecao[0])
        projeto_id = item['values'][0]
        self.nome_projeto = item['values'][1]
        
        # Define o resultado
        self.resultado = projeto_id
        
        # Fecha o diálogo
        self.destroy()


class ImportarSinapi(DialogBase):
    """Diálogo para importar dados do SINAPI"""
    
    def __init__(self, parent, db):
        super().__init__(parent, "Importar SINAPI", (600, 500))
        self.db = db
        
        # Variáveis
        self.arquivo_var = tk.StringVar()
        self.mes_ref_var = tk.StringVar(value=datetime.now().strftime("%Y-%m"))
        
        # Widgets
        ctk.CTkLabel(self.main_frame, text="Arquivo Excel SINAPI:", 
                   font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        file_frame = ctk.CTkFrame(self.main_frame)
        file_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkEntry(file_frame, textvariable=self.arquivo_var, width=400).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(file_frame, text="Procurar...", 
                    command=self._selecionar_arquivo).pack(side="right", padx=(5, 0))
        
        ctk.CTkLabel(self.main_frame, text="Mês de Referência (YYYY-MM):", 
                   font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        ctk.CTkEntry(self.main_frame, textvariable=self.mes_ref_var, width=100).pack(anchor="w", pady=(0, 15))
        
        ctk.CTkLabel(self.main_frame, text="Dados a importar:", 
                   font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.importar_insumos_var = tk.BooleanVar(value=True)
        self.importar_comp_var = tk.BooleanVar(value=True)
        
        ctk.CTkCheckBox(self.main_frame, text="Insumos", variable=self.importar_insumos_var).pack(anchor="w")
        ctk.CTkCheckBox(self.main_frame, text="Composições", variable=self.importar_comp_var).pack(anchor="w", pady=(0, 15))
        
        # Lista de status da importação
        ctk.CTkLabel(self.main_frame, text="Log de importação:", 
                   font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        log_frame = ctk.CTkFrame(self.main_frame)
        log_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        self.status_text = ctk.CTkTextbox(log_frame, height=200)
        self.status_text.pack(fill="both", expand=True)
        
        # Botões
        btn_frame = ctk.CTkFrame(self.main_frame)
        btn_frame.pack(fill="x")
        
        ctk.CTkButton(btn_frame, text="Fechar", command=self.destroy).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Importar", command=self._importar).pack(side="right", padx=5)
    
    def _selecionar_arquivo(self):
        """Abre o diálogo para selecionar o arquivo Excel"""
        arquivo = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx;*.xls")])
        if arquivo:
            self.arquivo_var.set(arquivo)
    
    def _importar(self):
        """Executa a importação dos dados SINAPI"""
        arquivo = self.arquivo_var.get().strip()
        if not arquivo or not os.path.exists(arquivo):
            messagebox.showerror("Erro", "Arquivo não encontrado")
            return
        
        mes_ref = self.mes_ref_var.get().strip()
        
        # Atualiza o status
        self.status_text.delete("1.0", ctk.END)
        self.status_text.insert(ctk.END, f"Iniciando importação...\n")
        self.update()
        
        try:
            # Importa insumos
            if self.importar_insumos_var.get():
                self.status_text.insert(ctk.END, "Importando insumos...\n")
                self.update()
                
                # Tenta importar da aba padrão e alternativas
                try:
                    total = self.db.importar_insumos(arquivo, aba='insumos', mes_ref=mes_ref)
                except Exception as e:
                    self.status_text.insert(ctk.END, f"Erro na aba 'insumos': {str(e)}\nTentando 'Insumos'...\n")
                    self.update()
                    try:
                        total = self.db.importar_insumos(arquivo, aba='Insumos', mes_ref=mes_ref)
                    except Exception as e:
                        self.status_text.insert(ctk.END, f"Erro na aba 'Insumos': {str(e)}\n")
                        self.update()
                        total = 0
                
                self.status_text.insert(ctk.END, f"Importados {total} insumos\n")
                self.update()
            
            # Importa composições
            if self.importar_comp_var.get():
                self.status_text.insert(ctk.END, "Importando composições...\n")
                self.update()
                
                # Tenta importar da aba padrão e alternativas
                try:
                    total = self.db.importar_composicoes(arquivo, aba='Composicoes', mes_ref=mes_ref)
                except Exception as e:
                    self.status_text.insert(ctk.END, f"Erro na aba 'Composicoes': {str(e)}\nTentando 'composicoes'...\n")
                    self.update()
                    try:
                        total = self.db.importar_composicoes(arquivo, aba='composicoes', mes_ref=mes_ref)
                    except Exception as e:
                        self.status_text.insert(ctk.END, f"Erro na aba 'composicoes': {str(e)}\n")
                        self.update()
                        total = 0
                
                self.status_text.insert(ctk.END, f"Importadas {total} composições\n")
                self.update()
            
            self.status_text.insert(ctk.END, "Importação concluída!")
            
            # Limpa os arquivos temporários
            self.db.limpar_arquivos_temporarios()
            
        except Exception as e:
            self.status_text.insert(ctk.END, f"Erro: {str(e)}")


class CalculadoraBDI(DialogBase):
    """Diálogo para calcular BDI"""
    
    def __init__(self, parent, db, projeto_id, bdi_atual=25.0):
        super().__init__(parent, "Calculadora de BDI", (500, 600))
        self.db = db
        self.projeto_id = projeto_id
        self.bdi_atual = bdi_atual
        self.resultado = None
        
        # Conteúdo
        ctk.CTkLabel(self.main_frame, text="Calculadora de BDI", 
                   font=("Segoe UI", 16, "bold")).pack(anchor="center", pady=(0, 20))
        
        # Componentes do BDI em um frame com scroll
        comp_scroll = ctk.CTkScrollableFrame(self.main_frame, height=400)
        comp_scroll.pack(fill="x", expand=True, pady=(0, 20))
        
        # Componentes do BDI
        components = [
            ("Administração Central (%)", 4.0),
            ("Seguro e Garantia (%)", 0.8),
            ("Risco (%)", 1.2),
            ("Despesas Financeiras (%)", 1.0),
            ("Lucro (%)", 7.0),
            ("Tributos - PIS+COFINS+ISS (%)", 5.65),
            ("CPRB (%)", 4.5)
        ]
        
        # Cria variáveis e campos para cada componente
        self.component_vars = []
        
        for i, (label, default) in enumerate(components):
            frame = ctk.CTkFrame(comp_scroll)
            frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(frame, text=label, width=250).pack(side="left")
            var = tk.StringVar(value=str(default).replace('.', ','))
            self.component_vars.append(var)
            ctk.CTkEntry(frame, textvariable=var, width=100).pack(side="right", padx=10)
        
        # Separador
        ctk.CTkLabel(self.main_frame, text="", height=1).pack(pady=5)
        
        # Campo para BDI manual
        manual_frame = ctk.CTkFrame(self.main_frame)
        manual_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(manual_frame, text="OU insira o BDI manualmente:", 
                   font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        bdi_frame = ctk.CTkFrame(manual_frame)
        bdi_frame.pack(fill="x")
        
        self.bdi_man_var = tk.StringVar(value=str(bdi_atual).replace('.', ','))
        ctk.CTkLabel(bdi_frame, text="BDI (%):", width=250).pack(side="left")
        ctk.CTkEntry(bdi_frame, textvariable=self.bdi_man_var, width=100).pack(side="right", padx=10)
        
        # Resultado
        result_frame = ctk.CTkFrame(self.main_frame)
        result_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(result_frame, text="BDI Calculado (%):", width=250).pack(side="left")
        self.resultado_var = tk.StringVar(value="---")
        ctk.CTkLabel(result_frame, textvariable=self.resultado_var, 
                   font=("Segoe UI", 12, "bold")).pack(side="right", padx=10)
        
        # Botões
        btn_frame = ctk.CTkFrame(self.main_frame)
        btn_frame.pack(fill="x", pady=20)
        
        ctk.CTkButton(btn_frame, text="Calcular", command=self._calcular).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Aplicar", command=self._aplicar).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Fechar", command=self.destroy).pack(side="right", padx=5)
    
    def _parse_value(self, value_str):
        """Converte string para float aceitando vírgula"""
        try:
            return float(value_str.replace(',', '.'))
        except ValueError:
            return None
    
    def _calcular(self):
        """Calcula o BDI conforme fórmula do TCU"""
        # Tenta converter todos os valores
        try:
            values = []
            for var in self.component_vars:
                value = self._parse_value(var.get())
                if value is None:
                    messagebox.showerror("Erro", "Um ou mais valores são inválidos")
                    return
                values.append(value / 100)  # Converte para decimal
            
            # Fórmula do BDI conforme Acórdão TCU
            ac, sg, r, df, l, t, cprb = values
            
            numerador = (1 + ac + sg + r + df) * (1 + l)
            denominador = 1 - (t + cprb)
            
            if denominador <= 0:
                messagebox.showerror("Erro", "A soma de tributos não pode ser maior ou igual a 100%")
                return
            
            bdi = (numerador / denominador - 1) * 100
            self.resultado_var.set(f"{bdi:.2f}%".replace('.', ','))
        except Exception as e:
            messagebox.showerror("Erro de cálculo", f"Erro ao calcular BDI: {str(e)}")
    
    def _aplicar(self):
        """Aplica o BDI calculado ao projeto"""
        # Obtém o BDI (calculado ou manual)
        bdi_valor = None
        
        if self.resultado_var.get() != "---":
            # Se foi calculado, usa esse valor
            try:
                bdi_valor = float(self.resultado_var.get().replace('%', '').replace(',', '.'))
            except ValueError:
                pass
        
        # Se não tiver calculado ou der erro, tenta o valor manual
        if bdi_valor is None:
            bdi_valor = self._parse_value(self.bdi_man_var.get())
            
        if bdi_valor is None:
            messagebox.showerror("Erro", "Valor de BDI inválido")
            return
        
        # Atualiza o BDI do projeto
        try:
            self.db.conn.execute(
                "UPDATE projetos SET bdi = ?, salvo = 0 WHERE id = ?", 
                (bdi_valor, self.projeto_id)
            )
            self.db.conn.commit()
            
            # Define o resultado para o chamador
            self.resultado = bdi_valor
            
            messagebox.showinfo("Sucesso", f"BDI atualizado para {bdi_valor:.2f}%".replace('.', ','))
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao atualizar BDI: {str(e)}")


class ConfiguracoesSistema(DialogBase):
    """Diálogo de configurações do sistema"""
    
    def __init__(self, parent, db):
        super().__init__(parent, "Configurações", (500, 400))
        self.db = db
        
        # Conteúdo
        ctk.CTkLabel(self.main_frame, text="Configurações do Sistema", 
                   font=("Segoe UI", 16, "bold")).pack(anchor="center", pady=(0, 20))
        
        # Seção de Banco de Dados
        ctk.CTkLabel(self.main_frame, text="Banco de Dados", 
                   font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        db_frame = ctk.CTkFrame(self.main_frame)
        db_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkButton(db_frame, text="Limpar Arquivos Temporários", 
                    command=self.db.limpar_arquivos_temporarios).pack(anchor="w", pady=5, padx=10)
        
        ctk.CTkButton(db_frame, text="Fazer Backup do Banco de Dados", 
                    command=self._backup_banco).pack(anchor="w", pady=5, padx=10)
        
        # Seção de Aparência
        ctk.CTkLabel(self.main_frame, text="Aparência", 
                   font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        appearance_frame = ctk.CTkFrame(self.main_frame)
        appearance_frame.pack(fill="x", pady=(0, 15))
        
        # Opções de tema
        ctk.CTkLabel(appearance_frame, text="Tema:").pack(anchor="w", pady=5, padx=10)
        
        theme_frame = ctk.CTkFrame(appearance_frame)
        theme_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkRadioButton(theme_frame, text="Claro", 
                         command=lambda: ctk.set_appearance_mode("Light")).pack(side="left", padx=10)
        ctk.CTkRadioButton(theme_frame, text="Escuro", 
                         command=lambda: ctk.set_appearance_mode("Dark")).pack(side="left", padx=10)
        ctk.CTkRadioButton(theme_frame, text="Sistema", 
                         command=lambda: ctk.set_appearance_mode("System")).pack(side="left", padx=10)
        
        # Botões
        btn_frame = ctk.CTkFrame(self.main_frame)
        btn_frame.pack(fill="x", pady=20)
        
        ctk.CTkButton(btn_frame, text="OK", command=self.destroy).pack(side="right", padx=5)
    
    def _backup_banco(self):
        """Faz um backup do banco de dados"""
        # Solicita o caminho para salvar o arquivo
        caminho = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db")],
            initialfile=f"backup_orcafacil_{datetime.now().strftime('%Y%m%d')}.db"
        )
        
        if not caminho:
            return
        
        try:
            # Faz uma cópia do arquivo de banco de dados
            import shutil
            shutil.copy2(self.db.db_path, caminho)
            messagebox.showinfo("Sucesso", f"Backup do banco de dados salvo em {caminho}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao fazer backup: {str(e)}")