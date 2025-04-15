#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Componentes UI customizados para o OrçaFácil
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from math import ceil

class ScrollableTreeView(ctk.CTkFrame):
    """
    TreeView com suporte a wrapping de texto e scrollbars
    Uma solução para o problema do wrap não ser suportado no ttk.Treeview
    """
    
    def __init__(self, master, columns, headings, column_widths, **kwargs):
        """
        Inicializa o TreeView com suporte a wrapping
        
        Args:
            master: Widget pai
            columns: Lista de nomes de colunas
            headings: Lista de textos dos cabeçalhos
            column_widths: Lista de larguras das colunas
        """
        super().__init__(master, **kwargs)
        
        self.columns = columns
        self.column_widths = column_widths
        
        # Cria um frame para o TreeView
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.pack(side="top", fill="both", expand=True)
        
        # Configura o grid para o TreeView e scrollbars
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        
        # Cria o TreeView
        self.tree = ttk.Treeview(
            self.tree_frame, 
            columns=columns,
            show="headings", 
            selectmode="browse"
        )
        
        # Configura as colunas e cabeçalhos
        for i, (col, heading, width) in enumerate(zip(columns, headings, column_widths)):
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=width//2)
        
        # Adiciona as scrollbars
        self.vsb = ctk.CTkScrollbar(self.tree_frame, orientation="vertical", command=self.tree.yview)
        self.hsb = ctk.CTkScrollbar(self.tree_frame, orientation="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        # Posiciona os widgets
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")
        
        # Configura as tags para linhas alternadas
        self.tree.tag_configure('odd', background='#EFEFEF')
        self.tree.tag_configure('even', background='#FFFFFF')
        
        # Vincula eventos para controlar o wrapping de texto
        self.tree.bind("<Configure>", self._on_configure)
        
        # Contador para rastreamento de itens
        self.count = 0
    
    def _on_configure(self, event=None):
        """Recalcula as larguras das colunas quando redimensionado"""
        if event and event.width > 10:  # Evita reconfigurações desnecessárias
            # Obtém largura disponível
            available_width = event.width - 10  # subtrai scrollbar
            
            # Ajusta larguras proporcionalmente
            total_width = sum(self.column_widths)
            for i, col in enumerate(self.columns):
                prop_width = int(available_width * (self.column_widths[i] / total_width))
                if prop_width > 20:  # Evita colunas muito estreitas
                    self.tree.column(col, width=prop_width)
    
    def _calculate_row_height(self, item_values, col_index):
        """Calcula a altura ideal para uma linha baseada no conteúdo"""
        # Obtém a largura da coluna
        col_width = self.tree.column(self.columns[col_index], "width")
        
        # Obtém o texto
        text = str(item_values[col_index])
        
        # Estima o número de caracteres por linha (média de 7 pixels por caractere)
        chars_per_line = max(1, int(col_width / 7))
        
        # Estima quantas linhas o texto vai ocupar
        lines = ceil(len(text) / chars_per_line) if chars_per_line > 0 else 1
        
        # Altura padrão de uma linha é cerca de 20 pixels
        # Retorna a altura necessária (mínimo de uma linha)
        return max(1, lines) * 20
    
    def insert(self, parent, index, values, tags=None):
        """
        Insere um item na TreeView com altura ajustada para o wrapping
        
        Args:
            parent: ID do item pai
            index: Índice onde inserir
            values: Valores para as colunas
            tags: Tags adicionais para o item
        """
        # Determina a tag de linha alternada
        if tags is None:
            tags = ()
        
        row_tag = 'odd' if self.count % 2 == 0 else 'even'
        all_tags = tags + (row_tag,)
        
        # Insere o item
        item_id = self.tree.insert(parent, index, values=values, tags=all_tags)
        
        # Incrementa o contador
        self.count += 1
        
        # Calcula a altura ideal para a descrição (coluna 3 normalmente)
        desc_idx = self.columns.index("descricao") if "descricao" in self.columns else 1
        row_height = self._calculate_row_height(values, desc_idx)
        
        # Configura a altura da linha
        self.tree.item(item_id, height=row_height)
        
        return item_id
    
    def delete(self, *items):
        """Deleta itens da TreeView"""
        self.tree.delete(*items)
    
    def get_children(self):
        """Retorna os IDs dos items filhos"""
        return self.tree.get_children()
    
    def selection(self):
        """Retorna os itens selecionados"""
        return self.tree.selection()
    
    def item(self, item_id, **options):
        """Acessa ou modifica as opções de um item"""
        return self.tree.item(item_id, **options)
    
    def pack(self, **kwargs):
        """Posiciona o widget usando o gerenciador pack"""
        super().pack(**kwargs)
        self._on_configure()  # Atualiza as larguras das colunas


class CustomCombobox(ctk.CTkFrame):
    """Combobox customizado com melhor estilo visual"""
    
    def __init__(self, master, values=None, command=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.values = values or []
        self.command = command
        self.current_value = tk.StringVar()
        
        # Cria o layout
        self.dropdown_frame = ctk.CTkFrame(self)
        self.dropdown_frame.pack(fill="x", expand=True)
        
        # Entrada de texto
        self.entry = ctk.CTkEntry(self.dropdown_frame, textvariable=self.current_value)
        self.entry.pack(side="left", fill="x", expand=True)
        
        # Botão dropdown
        self.dropdown_button = ctk.CTkButton(
            self.dropdown_frame, 
            text="▼", 
            width=30, 
            command=self._show_dropdown
        )
        self.dropdown_button.pack(side="right")
        
        # Menu dropdown (inicialmente escondido)
        self.dropdown_menu = None
    
    def _show_dropdown(self):
        """Mostra o menu dropdown"""
        if self.dropdown_menu:
            self.dropdown_menu.destroy()
        
        # Cria um toplevel para o menu
        self.dropdown_menu = ctk.CTkToplevel()
        self.dropdown_menu.withdraw()  # Esconde inicialmente para configurar
        
        # Configurações de janela
        self.dropdown_menu.overrideredirect(True)  # Remove decorações de janela
        
        # Cria os itens do menu
        for value in self.values:
            btn = ctk.CTkButton(
                self.dropdown_menu,
                text=value,
                anchor="w",
                command=lambda v=value: self._select_item(v)
            )
            btn.pack(fill="x")
        
        # Posiciona o menu abaixo do combobox
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        
        # Define tamanho e posição
        self.dropdown_menu.geometry(f"{self.entry.winfo_width()+30}x{min(200, len(self.values)*30)}+{x}+{y}")
        
        # Mostra o menu
        self.dropdown_menu.deiconify()
        
        # Configura para fechar quando perder o foco
        self.dropdown_menu.bind("<FocusOut>", lambda e: self.dropdown_menu.destroy())
        self.dropdown_menu.focus_set()
    
    def _select_item(self, value):
        """Seleciona um item do dropdown"""
        self.current_value.set(value)
        if self.dropdown_menu:
            self.dropdown_menu.destroy()
            self.dropdown_menu = None
        
        if self.command:
            self.command(value)
    
    def get(self):
        """Retorna o valor atual"""
        return self.current_value.get()
    
    def set(self, value):
        """Define o valor"""
        self.current_value.set(value)