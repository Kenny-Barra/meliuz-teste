# Relatório do teste A/B — Cashback Parceiro B — Mai-Jun 2011

## Decisão: qual variante escalar para 100%

### ➡️ Escalar o Grupo 1 para 100% do tráfego

**Nível de confiança:** alta

Escalar o Grupo 1 significa manter a configuração atual de cashback. As variantes testadas tiveram margem significativamente menor, ou seja, aumentar o cashback piorou o resultado para o Méliuz neste parceiro.

## Ficha do teste

- **Parceiro:** Parceiro B
- **Período:** 2011-05-01 a 2011-06-30
- **Variantes testadas:** 3
- **Descrição:** Teste de 3 níveis de cashback no Parceiro B
- **GMV total no teste:** R$ 9.586.800
- **Margem líquida total:** R$ 482.320

## Análise aprofundada

### Métricas por grupo

| Grupo | Compradores | GMV | Comissão | Cashback | Margem líquida | Margem % GMV | Ticket médio |
|---|---|---|---|---|---|---|---|
| Grupo 1 | 7.990 | R$ 4.093.818 | R$ 450.321 | R$ 163.751 | R$ 286.570 | 7,0% | R$ 512 |
| Grupo 2 | 5.452 | R$ 2.863.019 | R$ 314.935 | R$ 171.778 | R$ 143.157 | 5,0% | R$ 525 |
| Grupo 3 | 5.029 | R$ 2.629.963 | R$ 289.290 | R$ 236.697 | R$ 52.593 | 2,0% | R$ 523 |

### Significância estatística

Grupo controle (referência): **Grupo 1**.

| Comparação | Diferença de margem vs controle | p-value | Significativo (p<0,05)? |
|---|---|---|---|
| Grupo 2 vs Grupo 1 | -50,0% | 0.0000 | Sim |
| Grupo 3 vs Grupo 1 | -81,6% | 0.0000 | Sim |

_O p-value mede a chance de a diferença observada ser fruto do acaso. Abaixo de 0,05, consideramos a diferença real (estatisticamente significativa)._

### Observações sobre os dados

Nenhuma anomalia detectada. Dados consistentes ao longo do período.

### Próximos passos

1. Manter o Grupo 1 (configuração atual) em 100% do tráfego do Parceiro B.
2. Investigar por que aumentar o cashback não gerou GMV suficiente para compensar a margem perdida.
3. Testar variações mais sutis de cashback (passos menores) antes de descartar a alavanca.
