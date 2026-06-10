# Relatório do teste A/B — Cashback Parceiro A — Jan-Abr 2011

## Decisão: qual variante escalar para 100%

### ➡️ Escalar o Grupo 1 para 100% do tráfego

**Nível de confiança:** alta

Escalar o Grupo 1 significa manter a configuração atual de cashback. As variantes testadas tiveram margem significativamente menor, ou seja, aumentar o cashback piorou o resultado para o Méliuz neste parceiro.

## Ficha do teste

- **Parceiro:** Parceiro A
- **Período:** 2011-01-01 a 2011-04-02
- **Variantes testadas:** 3
- **Descrição:** Teste de 3 níveis de cashback no Parceiro A
- **GMV total no teste:** R$ 18.814.125
- **Margem líquida total:** R$ 1.026.517

## Análise aprofundada

### Métricas por grupo

| Grupo | Compradores | GMV | Comissão | Cashback | Margem líquida | Margem % GMV | Ticket médio |
|---|---|---|---|---|---|---|---|
| Grupo 1 | 9.633 | R$ 5.605.173 | R$ 638.135 | R$ 233.424 | R$ 404.711 | 7,2% | R$ 582 |
| Grupo 2 | 10.814 | R$ 6.423.096 | R$ 728.178 | R$ 370.659 | R$ 357.519 | 5,6% | R$ 594 |
| Grupo 3 | 11.410 | R$ 6.785.856 | R$ 767.887 | R$ 503.600 | R$ 264.287 | 3,9% | R$ 595 |

### Significância estatística

Grupo controle (referência): **Grupo 1**.

| Comparação | Diferença de margem vs controle | p-value | Significativo (p<0,05)? |
|---|---|---|---|
| Grupo 2 vs Grupo 1 | -11,7% | 0.1315 | Não |
| Grupo 3 vs Grupo 1 | -34,7% | 0.0000 | Sim |

_O p-value mede a chance de a diferença observada ser fruto do acaso. Abaixo de 0,05, consideramos a diferença real (estatisticamente significativa)._

### Observações sobre os dados

Nenhuma anomalia detectada. Dados consistentes ao longo do período.

### Próximos passos

1. Manter o Grupo 1 (configuração atual) em 100% do tráfego do Parceiro A.
2. Investigar por que aumentar o cashback não gerou GMV suficiente para compensar a margem perdida.
3. Testar variações mais sutis de cashback (passos menores) antes de descartar a alavanca.
