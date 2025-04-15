import sys

# Lista das bibliotecas que precisamos testar
bibliotecas = [
    "tkinter", "pandas", "sqlite3", "openpyxl", 
    "tempfile", "shutil", "re", "glob"
]

print("=== DIAGNÓSTICO DO SISTEMA ===")
print(f"Python versão: {sys.version}")
print("\nVerificando bibliotecas necessárias...")

for lib in bibliotecas:
    try:
        exec(f"import {lib}")
        print(f"✅ {lib}: OK")
    except Exception as e:
        print(f"❌ {lib}: ERRO - {str(e)}")

print("\nTestando inicialização do Tkinter...")
try:
    import tkinter as tk
    root = tk.Tk()
    root.title("Teste")
    print("✅ Tkinter inicializado com sucesso!")
    root.destroy()
except Exception as e:
    print(f"❌ Erro ao inicializar Tkinter: {str(e)}")

print("\nDiagnóstico concluído!")