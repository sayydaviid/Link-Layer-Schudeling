# Quantumnet

Este projeto simula uma rede quântica para transmissão de informações entre um remetente e um destinatário. A rede é projetada com diferentes topologias, abrangendo todas as camadas necessárias para um funcionamento eficiente. O repositório contém os códigos em Python para execução da simulação.

## Descrição
O repositório inclui os componentes essenciais da rede e do host, além dos qubits e pares EPR. Pode haver visualização de três tipos de topologia: anel, linha e grade. O projeto também abrange todas as camadas necessárias, desde a física até a aplicação, garantindo o funcionamento completo da rede quântica.

## Diretórios
- **quantumnet**:
  - `/components`: Arquivos básicos para o realização das simulações.
  - `/layers`: Arquivos que contêm as camadas para o funcionamento básico da rede.
  - `/objects`: Elementos essenciais para o funcionamento dos componentes.

## Camada de Enlace (`LinkLayer`)

A camada de enlace é responsável pela criação e manutenção do emaranhamento quântico entre pares de nós na rede. Esta camada realiza a gestão dos pares de EPRs (Einstein-Podolsky-Rosen) criados para viabilizar a comunicação quântica, além de aplicar técnicas de purificação de fidelidade quando necessário. A seguir estão as funcionalidades principais dessa camada:

- **Gerenciamento de EPRs**: Controla a criação e o uso dos EPRs ao longo das conexões. Cada solicitação de emaranhamento entre dois nós envolve o aumento do contador de EPRs e qubits utilizados.

- **Purificação de Fidelidade**: A `LinkLayer` possui métodos para melhorar a fidelidade dos pares EPRs através de protocolos de purificação, como `symmetric` (purificação simétrica) e `pumping` (purificação por bombardeamento). Estes métodos garantem que a comunicação entre os nós tenha uma qualidade satisfatória, reduzindo os erros de emaranhamento.

- **Protocolos de Emaranhamento**: A camada utiliza o protocolo de criação de emaranhamento com sinalização, gerenciado pela camada física, para estabelecer pares de EPRs entre os nós.

- **Agendamento e Verificação de EPRs**: Antes de iniciar uma purificação, a camada de enlace verifica se há EPRs suficientes. Caso contrário, novos pares são criados conforme necessário. Este mecanismo evita falhas por falta de recursos durante os processos de purificação.

- **Cálculo de Fidelidade Média**: A `LinkLayer` calcula a fidelidade média dos EPRs criados, proporcionando uma métrica geral de qualidade do emaranhamento para monitoramento e diagnóstico da rede.

## Funcionalidades Principais da `LinkLayer`

1. **`request`**: Solicita a criação de emaranhamento entre dois nós, tentando múltiplas vezes em caso de falha.
2. **`purification_calculator`**: Calcula a fidelidade resultante de um par de EPRs após a aplicação de uma das técnicas de purificação.
3. **`purification`**: Realiza a purificação de fidelidade em pares de EPRs, melhorando a qualidade do emaranhamento.
4. **`avg_fidelity_on_linklayer`**: Calcula e retorna a fidelidade média de todos os EPRs criados.
5. **`purification_scheduling`**: Agendamento de purificação para diferentes protocolos (`symmetric` ou `pumping`).
6. **`scheduling_verify`**: Garante a disponibilidade de EPRs necessários antes de cada tentativa de purificação, criando-os quando necessário.

Essas funcionalidades permitem que a camada de enlace gerencie de forma eficiente o emaranhamento e as operações de purificação, assegurando uma comunicação quântica confiável e de alta fidelidade entre os nós da rede.
