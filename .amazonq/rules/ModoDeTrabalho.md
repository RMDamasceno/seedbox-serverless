# Guia de Trabalho do Desenvolvedor: Seedbox Serverless AWS

Este documento estabelece o fluxo de trabalho, planejamento estratégico e as melhores práticas para um desenvolvedor único atuando no projeto **Seedbox Serverless AWS v1.5**. Como o projeto possui uma arquitetura serverless bem definida e aprovada, o foco do desenvolvedor deve ser a execução disciplinada, garantindo segurança, idempotência e baixo custo operacional.

## 1. Planejamento Estratégico e Análise de Demanda

Como desenvolvedor único, você é responsável por todas as fases do projeto. O planejamento estratégico deve ser iterativo e focado em entregas de valor contínuas, minimizando o risco de refatorações profundas. Antes de escrever qualquer código, é fundamental dominar a arquitetura proposta no documento técnico v1.5. O sistema baseia-se em um frontend React hospedado no S3 e distribuído via Cloudflare, um backend composto por API Gateway e AWS Lambda utilizando Python 3.12, e um worker executado em uma instância EC2 Spot (t3.medium) com Transmission. O armazenamento e o controle de estado são gerenciados inteiramente pelo Amazon S3 através de arquivos JSON.

Para manter o controle e facilitar os testes, o desenvolvimento deve ser estruturado em fases lógicas, conforme detalhado na tabela abaixo:

| Fase | Foco Principal | Principais Entregáveis |
|------|----------------|------------------------|
| 1 | Infraestrutura Base (IaC) | Criação de IAM Roles, Security Groups, Secrets Manager, buckets S3 com políticas restritivas e configuração inicial do API Gateway e Lambdas. |
| 2 | Backend e Estado | Implementação do protocolo de consistência S3 (COPY → VALIDATE → DELETE com ETag), rotas da API e autenticação JWT. |
| 3 | Worker EC2 e Integração | Criação do Launch Template, desenvolvimento do script Python do worker (polling, RPC, rclone) e gerenciamento de disco. |
| 4 | Frontend e Cloudflare | Desenvolvimento da interface React e configuração de DNS, Proxy, SSL e WAF na Cloudflare. |

## 2. Ciclo de Desenvolvimento Iterativo

Para cada componente ou funcionalidade, o desenvolvedor deve seguir um ciclo rigoroso de planejamento, desenvolvimento, análise, testes e melhoria contínua.

Durante o planejamento, é necessário revisar os contratos de API e schemas JSON definidos no documento técnico, identificar dependências arquiteturais e definir os critérios de aceite para a funcionalidade. O desenvolvimento deve priorizar a Infraestrutura como Código (IaC) utilizando AWS CDK ou Terraform, evitando configurações manuais no console da AWS para garantir a reprodutibilidade. O código deve ser limpo e modular, separando, por exemplo, a lógica de polling do S3 da lógica de controle do Transmission no worker. O tratamento de erros deve ser robusto, com logs detalhados para chamadas de rede.

A análise e correção envolvem revisões de código próprias (self-review) para verificar se a implementação atende aos requisitos de idempotência e concorrência, além de corrigir gargalos de performance ou falhas lógicas. A fase de testes é crítica e deve abranger testes unitários focados na lógica de transição de estado, testes de integração para validar a comunicação entre os componentes, e a execução rigorosa dos cenários de falha controlada descritos no documento técnico. Por fim, a verificação de pontos de melhoria exige a análise de logs no CloudWatch para identificar comportamentos anômalos e refinar configurações de timeout e memória.

## 3. Boas Práticas de Desenvolvimento

Como o sistema não utiliza banco de dados relacional, a consistência depende inteiramente do S3. A idempotência e o controle de concorrência são fundamentais.

Sempre utilize ETags ao atualizar o estado de um download, empregando a diretiva `CopySourceIfMatch` para garantir que outro processo não alterou o arquivo simultaneamente. O frontend deve gerar um UUID (Client Request ID) para cada requisição de criação, e o backend deve verificar a existência do objeto de idempotência no S3 antes de processar a requisição, evitando duplicações em caso de retries de rede.

A resiliência do sistema é garantida por uma política de retry adequada. O worker deve implementar backoff exponencial para falhas temporárias, enquanto erros definitivos devem mover o item para o estado cancelado sem retries infinitos. O gerenciamento de custos também é uma prioridade, exigindo que a instância EC2 seja desligada após três ciclos ociosos, a utilização da classe de armazenamento `INTELLIGENT_TIERING` no S3 e o monitoramento constante de alarmes de custo e uso.

## 4. Segurança

A segurança é um pilar crítico da arquitetura, mesmo para um projeto de uso pessoal, e deve ser aplicada em múltiplas camadas.

| Camada de Segurança | Práticas Recomendadas |
|---------------------|-----------------------|
| IAM (Menor Privilégio) | Restringir Lambdas e Worker EC2 apenas aos prefixos S3 e ações estritamente necessárias. |
| Proteção de Segredos | Utilizar AWS Secrets Manager para armazenar o segredo JWT e credenciais do Transmission; nunca hardcode credenciais. |
| Proteção de Borda | Configurar o S3 Website Endpoint para aceitar apenas IPs da Cloudflare, habilitar WAF e validar CORS no API Gateway. |

## 5. Conclusão

Trabalhar como desenvolvedor único no Seedbox Serverless AWS exige disciplina na execução e rigor nos testes. Ao seguir este guia, focando em IaC, testes de falha controlada e segurança desde o design, você garantirá a entrega de um sistema robusto, de baixo custo e com zero manutenção operacional quando ocioso.
