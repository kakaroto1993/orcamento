import tkinter as tk
from tkinter import ttk, messagebox

try:
    # Tenta inicializar a aplicação básica
    root = tk.Tk()
    root.title("OrçaFácil - Versão Mínima")
    root.geometry("500x300")
    
    # Adiciona um rótulo simples
    label = ttk.Label(root, text="Se você está vendo esta mensagem, o Tkinter está funcionando!")
    label.pack(pady=50)
    
    # Adiciona um botão de teste
    def teste_clique():
        messagebox.showinfo("Teste", "O sistema básico está funcionando!")
    
    button = ttk.Button(root, text="Clique Aqui", command=teste_clique)
    button.pack()
    
    # Inicia o loop principal
    print("Iniciando aplicação...")
    root.mainloop()
    print("Aplicação encerrada normalmente")
except Exception as e:
    # Se der qualquer erro, mostra no console
    import traceback
    print("ERRO AO INICIAR APLICAÇÃO:")
    print(str(e))
    traceback.print_exc()