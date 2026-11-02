# Protótipo de planejador KingsAge

O planejador **não executa ações no jogo**. Recebe um estado observado em JSON e devolve a próxima decisão para a meta `castle = 10`. Os números de `example-state.json` são **hipotéticos**, não custos do jogo. O observador CDP lê o estado do navegador separado; `castle5_once.py` é um executor independente e específico para uma única tentativa de Castelo 4→5, **não conectado ao planejador**. Não execute esse script sem revisar o mundo, a aldeia, o custo e a autorização.

```sh
python3 -m pip install -r requirements.txt
python3 planner.py example-state.json --mode planning
python3 planner.py example-state.json --mode autonomous
python3 -m unittest discover -s tests -v
```

No modo `planning`, toda ação proposta recebe `approval_required`. No modo `autonomous`, apenas `castle` e `warehouse` recebem `ready`; outros edifícios exigem aprovação. `ready` é só uma decisão do planejador: **não há executor conectado**. Quando a fila não está vazia, ele espera. Ele resolve requisitos de edifícios um nível por vez, detecta custos acima da capacidade do armazém e bloqueia quando faltam custos observados. Recursos insuficientes resultam em espera, ainda sem estimativa de tempo nem estratégia para produção.

Formato mínimo: `buildings` (níveis atuais), `resources` (quantidades), `capacity` (por recurso), `queue` (construções em curso), `next_levels` (custo e requisitos observados para o próximo nível de cada edifício relevante). Não preencha custos/requisitos por suposição: obtenha-os da interface da sua conta.

## Sondagem de conexão (somente leitura)

```sh
python3 connection.py https://s16-br.kingsage.gameforge.com/
```

Esta sondagem consulta a ajuda pública e uma página de jogo sem autenticação. Retorna JSON compacto com disponibilidade da ajuda e estado de autenticação. **Não extrai estado da conta, não faz login e não envia comandos.** A URL de aldeia é aceita, mas o parâmetro de aldeia não é enviado na sondagem anônima.

`browser_snapshot.js` é uma alternativa de reconhecimento **manual**, somente leitura: após fazer login no seu próprio navegador, abra o Console das ferramentas de desenvolvedor, execute o script e revise o JSON antes de compartilhá-lo. Ele coleta caminhos (sem query/hash), nomes de campos (sem valores) e trechos de texto associados a recursos/construções; **não lê cookies, senhas nem envia dados pela rede**. O arquivo foi checado sintaticamente, mas não testado numa página autenticada; elementos de interface podem exigir ajustes. Não compartilhe URLs de sessão, tokens, cookies ou HTML bruto.

## Login no navegador isolado (experimental)

`login_viewer.py` oferece um visualizador temporário do Chromium headless via HTTPS **somente na sub-rede privada escolhida** (pode ser a interface host↔VM). O navegador mantém perfil próprio em `.browser-profile` (permissão 0700); a porta CDP fica restrita a `127.0.0.1`. O visualizador aceita uma única conexão de usuário, ticket de ingresso único, cookie Secure/HttpOnly/SameSite e expira o acesso após 30 minutos. Não envie senhas ou cookies no chat. O certificado TLS é autossinado: confira a impressão digital SHA-256 com o valor comunicado separadamente antes de prosseguir. O enlace funciona apenas se seu dispositivo alcança o IP privado escolhido; não exponha a porta 8443 na internet. Feche o visualizador depois da autenticação. A sessão persistente do navegador não equivale a autorização para construir.

Para iniciar em outra ocasião: inicie Chromium headless com perfil privado e CDP somente em loopback; crie certificado para o IP LAN, ticket aleatório em arquivo de permissão 0600 e execute `python3 login_viewer.py --bind <IP_LAN> --lan <SUB_REDE/24> --cert <CERT> --key <KEY> --ticket-file <TICKET>`. O servidor remove o arquivo do ticket ao iniciar. **Não divulgue a porta de depuração nem o diretório do perfil.**

`snapshot.py` lê pela entrada padrão o JSON revisado da página (`python3 snapshot.py < snapshot.json`) e produz um estado compacto **parcial**. Aceita listas ou listas serializadas como string em `hints`/`elements`; extrai somente os IDs explícitos `wood`, `stone`, `iron` e o texto explícito `Castelo (Nível N)`. Fila, capacidade, trabalhadores e custo seguinte permanecem desconhecidos, portanto essa saída **não** pode ser entregue ao planejador como estado completo nem autoriza construção. Não publique capturas reais da aldeia nem links, cookies ou parâmetros de sessão.

## Observador e execução delimitada

`live_observer.py` lê somente a página de construções da aldeia selecionada em um Chrome dedicado encaminhado por SSH. Exige página autenticada e verifica mundo, aldeia, recursos, capacidade, trabalhadores, fila e custo do próximo nível do Castelo. Passe `--host` e `--village` explicitamente. Em Windows, execute `start-local-browser.ps1 -GameUrl 'https://<mundo>.kingsage.gameforge.com/?village=<id>' -VmTarget 'usuario@host-da-vm' -VmFingerprint 'SHA256:<fingerprint-verificado>'` com os valores reais (sem os sinais `< >`). Verifique o fingerprint da VM por canal confiável antes de usar o túnel; o script não valida automaticamente a chave SSH.

`castle5_once.py` foi feito para **uma única tentativa** de Castelo 4→5 no mundo/aldeia indicados em `KINGSAGE_HOST` e `KINGSAGE_VILLAGE` (variáveis obrigatórias). Revalida estado, custos, trabalhadores e fila, envia a ação no máximo uma vez e exige confirmação da fila ou do nível **e** do desconto dos recursos. Não o agende repetidamente: resultado ambíguo exige inspeção manual. A versão pública é uma adaptação saneada do script local e não substitui automaticamente a cópia instalada no agendador. Esse executor não implementa Castelo 6→10 nem se integra automaticamente ao planejador.

A skill `skills/goal-directed-game-agents/` contém o método geral de agentes de jogo e as referências sobre construções no KingsAge e login federado. É uma cópia de documentação, não instala automaticamente uma skill no Hermes.

**Segurança:** este repositório contém apenas código, testes, exemplo fictício e documentação. Não inclua `.browser-profile`, `.login-viewer`, `__pycache__`, capturas reais, tickets de acesso, certificados privados ou cookies. A automação pode contrariar regras do jogo; confira as regras aplicáveis antes de utilizar.
