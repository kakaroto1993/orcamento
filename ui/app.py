#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Interface gráfica principal do OrçaFácil
Contém a classe principal da aplicação
"""

import os
import sys
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime

# Importações internas
from database.sinapi import SinapiManager
from ui.components import ScrollableTreeView
from ui.dialogs import (
    NovoProjeto, 
    AbrirProjeto, 
    ImportarSinapi, 
    CalculadoraBDI,
    ConfiguracoesSistema
)


class OrcamentoApp:
    """Classe principal da interface gráfica do OrçaFácil"""
    
    def __init__(self, root):
        """Inicializa a aplicação"""
        self.root = root
        self.root.title("OrçaFácil - Sistema de Orçamento para Obras")
        self.root.geometry("1200x700")
        
        # Inicializa o banco de dados
        self.db = SinapiManager()
        
        # Variáveis
        self.projeto_atual = None
        self.termo_pesquisa = tk.StringVar()
        self.tipo_pesquisa = tk.StringVar(value="insumo")
        self.quantidade = tk.DoubleVar(value=1.0)
        
        # Configura o fechamento adequado
        self.root.protocol("WM_DELETE_WINDOW", self.fechar_aplicacao)
        
        # Configuração da interface
        self.create_menu()
        self.create_widgets()
        
        # Atualiza a lista de projetos
        self.atualizar_lista_projetos()
    
    def create_menu(self):
        """Cria a barra de menu da aplicação"""
        # CustomTkinter não tem menu, então usamos o menu padrão do tkinter
        menubar = tk.Menu(self.root)
        
        # Menu Arquivo
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Novo Projeto", command=self.novo_projeto)
        filemenu.add_command(label="Abrir Projeto", command=self.abrir_projeto)
        filemenu.add_command(label="Salvar", command=self.salvar_projeto)
        filemenu.add_separator()
        filemenu.add_command(label="Importar SINAPI", command=self.importar_sinapi)
        filemenu.add_separator()
        filemenu.add_command(label="Exportar para Excel", command=self.exportar_excel)
        filemenu.add_separator()
        filemenu.add_command(label="Sair", command=self.fechar_aplicacao)
        menubar.add_cascade(label="Arquivo", menu=filemenu)
        
        # Menu Ferramentas
        toolsmenu = tk.Menu(menubar, tearoff=0)
        toolsmenu.add_command(label="Calcular BDI", command=self.calcular_bdi)
        toolsmenu.add_command(label="Configurações", command=self.configuracoes)
        menubar.add_cascade(label="Ferramentas", menu=toolsmenu)
        
        # Menu Ajuda
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Manual do Usuário", command=self.manual)
        helpmenu.add_command(label="Sobre", command=self.sobre)
        menubar.add_cascade(label="Ajuda", menu=helpmenu)
        
        self.root.config(menu=menubar)
        
        # Adiciona atalhos de teclado
        self.root.bind("<Control-n>", lambda event: self.novo_projeto())
        self.root.bind("<Control-o>", lambda event: self.abrir_projeto())
        self.root.bind("<Control-s>", lambda event: self.salvar_projeto())
    
    def create_widgets(self):
        """Cria os widgets da interface principal"""
        # Frame principal
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame superior - Informações do projeto
        proj_frame = ctk.CTkFrame(main_frame)
        proj_frame.pack(fill="x", pady=5)
        
        proj_label = ctk.CTkLabel(proj_frame, text="Projeto", font=("Segoe UI", 12, "bold"))
        proj_label.pack(anchor="w", padx=10, pady=5)
        
        # Grid para organizar as informações do projeto
        proj_info_frame = ctk.CTkFrame(proj_frame)
        proj_info_frame.pack(fill="x", expand=True, padx=10, pady=5)
        
        # Organizando em um grid mais moderno
        info_grid = ctk.CTkFrame(proj_info_frame)
        info_grid.pack(fill="x", expand=True)
        
        # Primeira linha do grid
        ctk.CTkLabel(info_grid, text="Projeto atual:").grid(row=0, column=0, sticky="w", padx=5)
        self.lbl_projeto = ctk.CTkLabel(info_grid, text="Nenhum projeto selecionado")
        self.lbl_projeto.grid(row=0, column=1, sticky="w", padx=5)
        
        ctk.CTkLabel(info_grid, text="Total:").grid(row=0, column=2, sticky="w", padx=(20,5))
        self.lbl_total = ctk.CTkLabel(info_grid, text="R$ 0,00", font=("Segoe UI", 10, "bold"))
        self.lbl_total.grid(row=0, column=3, sticky="w", padx=5)
        
        ctk.CTkLabel(info_grid, text="BDI:").grid(row=0, column=4, sticky="w", padx=(20,5))
        self.lbl_bdi = ctk.CTkLabel(info_grid, text="25%")
        self.lbl_bdi.grid(row=0, column=5, sticky="w", padx=5)
        
        ctk.CTkLabel(info_grid, text="Total com BDI:").grid(row=0, column=6, sticky="w", padx=(20,5))
        self.lbl_total_bdi = ctk.CTkLabel(info_grid, text="R$ 0,00", font=("Segoe UI", 10, "bold"))
        self.lbl_total_bdi.grid(row=0, column=7, sticky="w", padx=5)
        
        # Indicador de não salvo
        self.lbl_salvo = ctk.CTkLabel(info_grid, text="Não Salvo", text_color="red")
        self.lbl_salvo.grid(row=0, column=8, sticky="e", padx=(50,5))
        self.lbl_salvo.grid_remove()  # Inicialmente oculto
        
        # Frame do meio - dividido em dois painéis
        mid_frame = ctk.CTkFrame(main_frame)
        mid_frame.pack(fill="both", expand=True, pady=10)
        
        # Configurando grid para os dois painéis lado a lado
        mid_frame.grid_columnconfigure(0, weight=1)
        mid_frame.grid_columnconfigure(1, weight=1)
        mid_frame.grid_rowconfigure(0, weight=1)
        
        # Painel esquerdo - Pesquisa e adição de itens
        left_frame = ctk.CTkFrame(mid_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Título do frame
        ctk.CTkLabel(left_frame, text="Adicionar Itens", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        
        # Frame de pesquisa
        search_frame = ctk.CTkFrame(left_frame)
        search_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(search_frame, text="Pesquisar:").pack(side="left")
        entry_search = ctk.CTkEntry(search_frame, textvariable=self.termo_pesquisa, width=250)
        entry_search.pack(side="left", padx=5)
        entry_search.bind("<Return>", lambda event: self.pesquisar())
        
        # Botões de rádio para tipo de pesquisa
        radio_frame = ctk.CTkFrame(search_frame)
        radio_frame.pack(side="left", padx=5)
        
        ctk.CTkRadioButton(radio_frame, text="Insumo", variable=self.tipo_pesquisa, value="insumo").pack(side="left")
        ctk.CTkRadioButton(radio_frame, text="Composição", variable=self.tipo_pesquisa, value="composicao").pack(side="left", padx=10)
        
        ctk.CTkButton(search_frame, text="Pesquisar", command=self.pesquisar).pack(side="left", padx=5)
        
        # Lista de resultados com nossa árvore customizada que suporta wrapping
        result_frame = ctk.CTkFrame(left_frame)
        result_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Aqui usaríamos nossa classe customizada que suporta wrapping
        self.tree_resultados = ScrollableTreeView(
            result_frame,
            columns=("codigo", "descricao", "unidade", "preco"),
            headings=["Código", "Descrição", "Unidade", "Preço"],
            column_widths=[100, 400, 80, 100]
        )
        self.tree_resultados.pack(fill="both", expand=True)
        
        # Frame para adicionar item ao orçamento
        add_frame = ctk.CTkFrame(left_frame)
        add_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(add_frame, text="Quantidade:").pack(side="left")
        entry_qtd = ctk.CTkEntry(add_frame, textvariable=self.quantidade, width=100)
        entry_qtd.pack(side="left", padx=5)
        # Permite tanto vírgula quanto ponto para decimais
        entry_qtd.bind("<FocusOut>", self.formatar_quantidade)
        
        ctk.CTkButton(add_frame, text="Adicionar ao Orçamento", command=self.adicionar_ao_orcamento).pack(side="left", padx=5)
        
        # Painel direito - Orçamento atual
        right_frame = ctk.CTkFrame(mid_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        
        # Título do frame
        ctk.CTkLabel(right_frame, text="Orçamento Atual", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        
        # Lista de itens do orçamento com nossa TreeView customizada
        orc_frame = ctk.CTkFrame(right_frame)
        orc_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Usando a classe customizada com suporte a wrapping
        self.tree_orcamento = ScrollableTreeView(
            orc_frame,
            columns=("id", "tipo", "codigo", "descricao", "unidade", "qtd", "preco", "total"),
            headings=["#", "Tipo", "Código", "Descrição", "Un", "Qtd", "Preço Un", "Total"],
            column_widths=[40, 80, 80, 300, 50, 80, 80, 80]
        )
        self.tree_orcamento.pack(fill="both", expand=True)
        
        # Botões de ação para orçamento
        action_frame = ctk.CTkFrame(right_frame)
        action_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(action_frame, text="Remover Item", command=self.remover_item).pack(side="left", padx=5)
        ctk.CTkButton(action_frame, text="Editar Quantidade", command=self.editar_quantidade).pack(side="left", padx=5)
        ctk.CTkButton(action_frame, text="Ver Composição", command=self.ver_composicao).pack(side="left", padx=5)
        
        # Frame inferior - Status
        bottom_frame = ctk.CTkFrame(main_frame)
        bottom_frame.pack(fill="x", pady=5)
        
        status_frame = ctk.CTkFrame(bottom_frame)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(status_frame, text="Status:").pack(side="left")
        self.lbl_status = ctk.CTkLabel(status_frame, text="Pronto")
        self.lbl_status.pack(side="left", padx=5)
    
    # Métodos para funcionalidades
    def atualizar_lista_projetos(self):
        """Atualiza a lista de projetos disponíveis"""
        self.projetos = self.db.listar_projetos()
    
    def novo_projeto(self):
        """Cria um novo projeto"""
        dialog = NovoProjeto(self.root, self.db)
        if dialog.resultado:
            # Atualiza a interface
            self.atualizar_lista_projetos()
            self.projeto_atual = dialog.resultado
            self.atualizar_interface()
            
            # Atualiza status
            self.lbl_status.configure(text=f"Projeto '{dialog.nome_projeto}' criado com sucesso!")
    
    def abrir_projeto(self):
        """Abre um projeto existente"""
        dialog = AbrirProjeto(self.root, self.db, self.projetos)
        if dialog.resultado:
            # Atualiza a interface
            self.projeto_atual = dialog.resultado
            self.atualizar_interface()
            
            # Atualiza status
            self.lbl_status.configure(text=f"Projeto '{dialog.nome_projeto}' aberto com sucesso!")
    
    def salvar_projeto(self):
        """Salva o projeto atual (exportando para Excel)"""
        if self.projeto_atual is None:
            messagebox.showinfo("Aviso", "Nenhum projeto aberto para salvar")
            return
        
        # Verifica se o projeto foi modificado
        projeto_info = None
        for p in self.projetos:
            if p[0] == self.projeto_atual:
                projeto_info = p
                break
        
        if projeto_info and projeto_info[6] == 1:  # Já está salvo
            messagebox.showinfo("Informação", "O projeto já está salvo")
            return
        
        # Solicita o caminho para salvar o arquivo
        nome_arquivo = f"{projeto_info[1].replace(' ', '_')}_orçamento.xlsx"
        caminho = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=nome_arquivo
        )
        
        if not caminho:
            return
        
        try:
            self.db.exportar_orcamento_excel(self.projeto_atual, caminho)
            self.lbl_salvo.grid_remove()  # Esconde o indicador de não salvo
            messagebox.showinfo("Sucesso", f"Projeto salvo em {caminho}")
            self.lbl_status.configure(text=f"Projeto salvo com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {str(e)}")
    
    def atualizar_interface(self):
            """Atualiza a interface com os dados do projeto atual"""
            if self.projeto_atual is None:
                self.lbl_projeto.configure(text="Nenhum projeto selecionado")
                self.lbl_total.configure(text="R$ 0,00")
                self.lbl_bdi.configure(text="25%")
                self.lbl_total_bdi.configure(text="R$ 0,00")
                try:
                    self.lbl_salvo.grid_remove()
                    self.tree_orcamento.delete(*self.tree_orcamento.get_children())
                except (AttributeError, tk.TclError) as e:
                    print(f"Aviso ao atualizar interface: {e}")
                return
        
            # Apenas para debug inicial
            messagebox.showinfo("Info", f"Projeto selecionado: {self.projeto_atual}")
            
            # Mostrar mensagem de não implementado até completarmos todas as funcionalidades
            messagebox.showinfo("Em desenvolvimento", 
                            "A função de carregar detalhes do projeto será implementada em breve!")
        
    def formatar_quantidade(self, event):
        """Formata o campo de quantidade para aceitar vírgula ou ponto"""
        try:
            texto = event.widget.get().replace(',', '.')
            valor = float(texto)
            self.quantidade.set(valor)
        except ValueError:
            # Se não for um número válido, reverte para 1.0
            self.quantidade.set(1.0)
    
    def pesquisar(self):
        """Pesquisa insumos ou composições"""
        # Implementação mínima
        pass
    
    def adicionar_ao_orcamento(self):
        """Adiciona o item selecionado ao orçamento"""
        # Implementação mínima
        pass
    
    def remover_item(self):
        """Remove o item selecionado do orçamento"""
        # Implementação mínima
        pass
    
    def editar_quantidade(self):
        """Edita a quantidade do item selecionado"""
        # Implementação mínima
        pass
    
    def ver_composicao(self):
        """Mostra os detalhes de uma composição"""
        # Implementação mínima
        pass
    
    def exportar_excel(self):
        """Exporta o orçamento para Excel"""
        # Implementação mínima
        pass
    
    def calcular_bdi(self):
        """Abre a calculadora de BDI"""
        # Implementação mínima
        pass
    
    def configuracoes(self):
        """Abre a janela de configurações do aplicativo"""
        # Implementação mínima
        pass
    
    def manual(self):
        """Mostra o manual do usuário"""
        messagebox.showinfo("Manual", "O manual do usuário será implementado em uma versão futura.")
    
    def sobre(self):
        """Mostra informações sobre o sistema"""
        messagebox.showinfo(
            "Sobre o OrçaFácil",
            "OrçaFácil 2.0 - Sistema de Orçamento para Obras\n\n"
            "Versão com interface modernizada usando CustomTkinter\n\n"
            "© 2023-2025 OrçaFácil - Todos os direitos reservados"
        )
        
    def importar_sinapi(self):
        """Importa dados do SINAPI"""
        dialog = ImportarSinapi(self.root, self.db)
        # O diálogo lida com a importação, aqui só atualizamos se necessário

    def fechar_aplicacao(self):
        """Manipula o fechamento da aplicação"""
        # Verifica se há projetos não salvos
        projetos_nao_salvos = []
        for projeto in self.projetos:
            if projeto[6] == 0:  # Não salvo
                projetos_nao_salvos.append(projeto[1])
        
        if projetos_nao_salvos:
            resposta = messagebox.askyesnocancel(
                "Projetos não salvos",
                f"Os seguintes projetos têm alterações não salvas:\n\n"
                f"{', '.join(projetos_nao_salvos)}\n\n"
                "Deseja salvar antes de sair?"
            )
            
            if resposta is None:  # Cancelar
                return
            elif resposta:  # Sim
                # Se o projeto atual não foi salvo, abre a janela de salvar
                if self.projeto_atual:
                    for projeto in self.projetos:
                        if projeto[0] == self.projeto_atual and projeto[6] == 0:
                            self.salvar_projeto()
                            break
        
        # Fecha o banco de dados
        self.db.fechar()
        
        # Fecha a aplicação
        self.root.destroy()