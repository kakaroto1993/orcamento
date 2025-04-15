#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modelos de dados para o OrçaFácil
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Union


@dataclass
class Insumo:
    """Representa um insumo SINAPI"""
    codigo: str
    descricao: str
    unidade: str
    preco_mediano: float
    origem: str = "SINAPI"
    data_referencia: str = ""
    data_atualizacao: str = ""


@dataclass
class Composicao:
    """Representa uma composição SINAPI"""
    codigo: str
    descricao: str
    unidade: str
    custo_total: float
    itens: List["ItemComposicao"] = None
    origem: str = "SINAPI"
    data_referencia: str = ""
    data_atualizacao: str = ""


@dataclass
class ItemComposicao:
    """Item de uma composição"""
    codigo_composicao: str
    codigo_insumo: str
    coeficiente: float
    descricao: str = ""
    unidade: str = ""
    preco: float = 0.0


@dataclass
class ItemOrcamento:
    """Item de um orçamento"""
    id: Optional[int]
    projeto_id: int
    tipo: str  # 'insumo' ou 'composicao'
    codigo: str
    descricao: str
    unidade: str
    quantidade: float
    preco_unitario: float
    
    @property
    def valor_total(self) -> float:
        """Calcula o valor total do item"""
        return self.quantidade * self.preco_unitario
    
    @property
    def valor_com_bdi(self, bdi: float) -> float:
        """Calcula o valor com BDI aplicado"""
        return self.valor_total * (1 + bdi/100)


@dataclass
class Projeto:
    """Representa um projeto de orçamento"""
    id: Optional[int]
    nome: str
    descricao: str
    data_criacao: str
    data_atualizacao: str
    bdi: float = 25.0
    salvo: bool = True
    itens: List[ItemOrcamento] = None
    
    @property
    def total_sem_bdi(self) -> float:
        """Calcula o total do orçamento sem BDI"""
        if not self.itens:
            return 0.0
        return sum(item.valor_total for item in self.itens)
    
    @property
    def total_com_bdi(self) -> float:
        """Calcula o total do orçamento com BDI"""
        return self.total_sem_bdi * (1 + self.bdi/100)
    
    @classmethod
    def from_db_row(cls, row):
        """Cria um objeto Projeto a partir de uma linha do banco de dados"""
        return cls(
            id=row[0],
            nome=row[1],
            descricao=row[2],
            data_criacao=row[3],
            data_atualizacao=row[4],
            bdi=row[5],
            salvo=bool(row[6]),
            itens=[]
        )