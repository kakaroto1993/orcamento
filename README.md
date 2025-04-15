# OrçaFácil 2.0

Sistema de Orçamento para Obras com interface moderna e código refatorado.

## Instalação

1. Crie um ambiente virtual:
```bash
python -m venv venv
```

2. Ative o ambiente virtual:
```bash
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Instale as dependências:
```bash
pip install customtkinter pandas
```

## Estrutura do Projeto

```
orcafacil/
├── main.py             # Ponto de entrada principal
├── database/           # Código de banco de dados
│   ├── __init__.py
│   └── sinapi.py       # Classe SinapiManager
├── models/             # Modelos de dados
│   ├── __init__.py
│   └── projeto.py      # Classes de dados
├── ui/                 # Interface gráfica
│   ├── __init__.py
│   ├── app.py          # Aplicação principal
│   ├── components.py   # Componentes personalizados
│   └── dialogs.py      # Diálogos e janelas
└── utils/              # Utilitários diversos
    └── __init__.py
```

## Execução

```bash
python main.py
```

## Características

- Interface modernizada com CustomTkinter
- Código refatorado e organizado em módulos
- Melhor manutenibilidade
- Componentes personalizados para resolver limitações do Tkinter

## Status do Projeto

Este projeto é uma refatoração do OrçaFácil original. Atualmente, implementamos:

- [x] Estrutura base modularizada
- [x] Interface modernizada com CustomTkinter
- [x] Correção do problema de texto longo no TreeView
- [ ] Implementação completa de todos os recursos originais
- [ ] Testes automatizados
- [ ] Documentação completa

## Próximos Passos

1. Completar a implementação de todas as funcionalidades
2. Adicionar testes automatizados
3. Melhorar a interface com mais componentes modernos
4. Criar um sistema de atualizações automáticas