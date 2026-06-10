# Relatório do teste A/B — Cashback Parceiro C — Jul-Ago 2011

## Decisão: qual variante escalar para 100%

### ➡️ Escalar o Grupo 1 para 100% do tráfego

**Nível de confiança:** alta

Escalar o Grupo 1 significa manter a configuração atual de cashback. As variantes testadas tiveram margem significativamente menor, ou seja, aumentar o cashback piorou o resultado para o Méliuz neste parceiro.

## Ficha do teste

- **Parceiro:** Parceiro C
- **Período:** 2011-07-01 a 2011-08-14
- **Variantes testadas:** 2
- **Descrição:** Teste de 2 variantes no Parceiro C (Grupo 2 com cashback máximo)
- **GMV total no teste:** R$ 3.423.695
- **Margem líquida total:** R$ 34.769

## Análise aprofundada

### Métricas por grupo

| Grupo | Compradores | GMV | Comissão | Cashback | Margem líquida | Margem % GMV | Ticket médio |
|---|---|---|---|---|---|---|---|
| Grupo 1 | 4.549 | R$ 1.738.460 | R$ 121.693 | R$ 86.924 | R$ 34.769 | 2,0% | R$ 382 |
| Grupo 2 | 4.522 | R$ 1.685.235 | R$ 117.967 | R$ 117.967 | R$ 0 | 0,0% | R$ 373 |

### Significância estatística

Grupo controle (referência): **Grupo 1**.

| Comparação | Diferença de margem vs controle | p-value | Significativo (p<0,05)? |
|---|---|---|---|
| Grupo 2 vs Grupo 1 | -100,0% | 0.0000 | Sim |

_O p-value mede a chance de a diferença observada ser fruto do acaso. Abaixo de 0,05, consideramos a diferença real (estatisticamente significativa)._

### Observações sobre os dados

Nenhuma anomalia detectada. Dados consistentes ao longo do período.

### Próximos passos

1. Manter o Grupo 1 (configuração atual) em 100% do tráfego do Parceiro C.
2. Investigar por que aumentar o cashback não gerou GMV suficiente para compensar a margem perdida.
3. Testar variações mais sutis de cashback (passos menores) antes de descartar a alavanca.
