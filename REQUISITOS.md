# KingsAge — requisitos documentados (Mundo 16 BR)

Consulta direta às páginas de ajuda públicas do servidor `s16-br.kingsage.gameforge.com` em 1º de novembro de 2026. São dados da **documentação desse mundo**, não uma observação da conta do usuário. O agente deve confirmar custos, disponibilidade, trabalhadores e fila na interface real antes de agir. `res1.png` é madeira, `res2.png` é pedra e `res3.png` é ferro (ícones verificados visualmente).

## Castelo até o nível 10

A página do castelo não apresenta seção de pré-requisitos de outros edifícios. Ela informa custo por nível, trabalhadores adicionais/total e fator de tempo. O custo da linha N é para construir o nível N, não um custo acumulado.

| Nível | Madeira | Pedra | Ferro | Trabalhadores adicionais / total | Fator de tempo |
|---:|---:|---:|---:|---:|---:|
| 1 | 70 | 85 | 65 | 2 / 2 | 100% |
| 2 | 82 | 99 | 76 | 0 / 2 | 96% |
| 3 | 95 | 116 | 88 | 1 / 3 | 93% |
| 4 | 111 | 136 | 103 | 0 / 3 | 89% |
| 5 | 129 | 159 | 120 | 0 / 3 | 86% |
| 6 | 150 | 186 | 139 | 1 / 4 | 82% |
| 7 | 175 | 218 | 163 | 0 / 4 | 79% |
| 8 | 204 | 255 | 189 | 0 / 4 | 76% |
| 9 | 238 | 298 | 221 | 1 / 5 | 73% |
| 10 | 277 | 349 | 257 | 1 / 6 | 71% |

Fonte: https://s16-br.kingsage.gameforge.com/help.php?build=main&m=buildings&sub=details

A tabela do armazém informa capacidade 1.000 no nível 1. Isso excede o maior custo individual documentado para qualquer nível do castelo até 10 (349 pedras); portanto, **se a capacidade exibida na conta for 1.000 para cada recurso**, não é necessário melhorar o armazém apenas para pagar esses níveis. Isso não elimina a necessidade de verificar capacidade real, recursos, trabalhadores disponíveis no moinho e estado da fila. A documentação do castelo mostra total de 6 trabalhadores no nível 10, e o moinho informa a capacidade de trabalhadores por nível.

Fontes: https://s16-br.kingsage.gameforge.com/help.php?build=storage&m=buildings&sub=details ; https://s16-br.kingsage.gameforge.com/help.php?build=farm&m=buildings&sub=details

## Requisitos estruturais de outros edifícios

Estas páginas mostram uma seção explícita `Requisitos` para a liberação do edifício (não para cada nível):

| Edifício | Requisito publicado |
|---|---|
| Esconderijo | Moinho 3 |
| Quartel | Armazém 3 + Moinho 3 |
| Muralha | Quartel 1 |
| Mercado | Armazém 5 |
| Estábulo | Mercado 1 |
| Alquimista | Quartel 5 |
| Mansão | Alquimista 5 |
| Joalheiro | Mansão 1 |
| Memorial | Castelo 50, Moinho 50, Serraria 50, Pedreira 50, Mina de Ferro 50, Armazém 50, Esconderijo 30, Mercado 30, Quartel 30, Estábulo 30, Alquimista 5, Mansão 10, Joalheiro 5 e Muralha 20 |

O castelo, pedreira, serraria, mina, armazém e moinho não exibem essa seção nas respectivas páginas. A ligação `city` no índice não é uma página de detalhes do edifício e foi excluída da tabela.

Índice: https://s16-br.kingsage.gameforge.com/help.php?m=buildings

Exemplos verificáveis: https://s16-br.kingsage.gameforge.com/help.php?build=barracks&m=buildings&sub=details ; https://s16-br.kingsage.gameforge.com/help.php?build=market&m=buildings&sub=details ; https://s16-br.kingsage.gameforge.com/help.php?build=statue&m=buildings&sub=details

## Impacto no protótipo

O arquivo `example-state.json` é *inteiramente hipotético*, não um retrato do jogo. Para a meta castelo 10, o planejador não deve inventar um requisito de armazém maior que 1 apenas porque o exemplo o ilustra. A documentação serve como catálogo de referência; a observação da conta/servidor prevalece para decisão e execução. O planejador isolado não lê nem age no jogo; `live_observer.py` e `castle5_once.py` são ferramentas separadas para leitura e ação única. O observador inclui trabalhadores livres e necessários, mas o planejador ainda não modela explicitamente os requisitos do moinho. Antes de conectar um executor contínuo ao planejador, adicionar ao estado capacidade/ocupação de trabalhadores e identificar quando uma construção requer um nível mínimo de moinho.
