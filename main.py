#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OrçaFácil - Sistema de Orçamento para Obras
Ponto de entrada principal da aplicação
"""

import sys
import os
import customtkinter as ctk  # Importamos CustomTkinter ao invés do Tkinter comum

# Importações internas
from ui.app import OrcamentoApp

def configurar_ambiente():
    """Configura o ambiente de execução"""
    # Configura o tema padrão do CustomTkinter
    ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"
    
    # Garante que o diretório de trabalho é o mesmo do script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Função principal que inicia a aplicação"""
    configurar_ambiente()
    
    # Cria a janela principal
    root = ctk.CTk()
    app = OrcamentoApp(root)
    
    # Inicia o loop principal
    root.mainloop()

if __name__ == "__main__":
    main()