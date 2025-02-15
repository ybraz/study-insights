## OSCP Success Stories Scraper & AI Analyzer
Este projeto um **script em Python** que coleta posts do subreddit **OSCP** (com foco na query
"passed"), filtrando histórias de sucesso detalhadas para a preparção da OSCP, e realiza uma análise
de insights acionáveis utilizando a API da OpenAI. Além disso, o script salva os posts e comentários
em um banco de dados **SQLite** para facilitar análises futuras.
## Funcionalidades
- **Coleta de Posts e Comentários:** Busca posts do subreddit *oscp* com base em uma query
específica ("passed") e filtra aqueles que contém conteúdo relevante e detalhado.
- **Armazenamento em SQLite:** Salva os posts e seus respectivos comentários em um banco de
dados SQLite, facilitando consultas e análises.
- **Análise com ChatGPT-4o (OpenAI):** Envia o conteúdo coletado para a API do OpenAI, que retorna insights
detalhados e práticos para futuros candidatos ao OSCP.
- **Logging Avançado:** Utiliza a biblioteca `logging` para registrar o andamento e possíveis erros
durante a execução do script.
## Pré-requisitos
- **Python 3.x**
- Ambiente virtual (recomendado)
- **API Keys configuradas:**
  - `REDDIT_CLIENT_ID`
  - `REDDIT_CLIENT_SECRET`
  - `REDDIT_USER_AGENT`
  - `OPENAI_API_KEY`
## Instalação
1. **Clone o repositório:**
 ```bash
 git clone https://github.com/marcostolosa/study-insights.git
 cd study-insights
 ```
2. **Crie e ative um ambiente virtual:**
 ```bash
 python3 -m venv scraper
 source scraper/bin/activate # Linux/MacOS
 # No Windows, use: scraper\Scripts\activate
 ```
3. **Instale as dependências:**
 ```bash
 pip3 install -r requirements.txt
 ```
 *Caso não possua um arquivo `requirements.txt`, você pode instalar manualmente:*
 ```bash
 python3 -m pip install praw openai==0.28
 ```
## Configurção das Variáveis de Ambiente
Certifique-se de configurar as seguintes variáveis de ambiente com suas respectivas API keys:
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`
- `OPENAI_API_KEY`

Você pode utilizar um arquivo `.env` ou configurar as variáveis diretamente no seu ambiente de
desenvolvimento.
## Como Usar
1. **Execute o script:**
 ```bash
 python3 oscpInsights.py
 ```
2. **Resultados:**
 - O banco de dados SQLite `oscp_posts.db` criado com as tabelas `posts` e `comments`.
 - Um arquivo de saída `oscp_success_analysis.txt` contendo a análise gerada pela API do OpenAI.
## Estrutura do Banco de Dados
- **Tabela `posts`:**
 - `id` (chave primária)
 - `title`
 - `selftext`
 - `url`
 - `created_utc`
- **Tabela `comments`:**
 - `id` (chave primária)
 - `post_id` (referência ao post)
 - `comment_body`
 - `created_utc`
## Como Funciona
1. **Integração com o Reddit:**
 - Utiliza a [PRAW](https://praw.readthedocs.io/en/stable/) para se conectar API do Reddit e
coletar posts do subreddit "oscp".
2. **Filtragem de Conteúdo:**
 - Apenas posts com conteúdo detalhado (com base em palavras-chave e tamanho mínimo) são
selecionados.
3. **Armazenamento em SQLite:**
 - Posts e seus comentários são inseridos em um banco de dados SQLite para armazenamento
persistente.
4. **Análise com ChatGPT-4o (OpenAI):**
 - O conteúdo coletado é enviado para a API do OpenAI
([Documentao](https://platform.openai.com/docs/api-reference/chat/create)) para extrair insights
detalhados sobre técnicas e estratégias de estudo.
5. **Registro de Logs:**
 - Utiliza o módulo `logging` para monitorar a execução e identificar possíveis erros ([Python
Logging](https://docs.python.org/3/library/logging.html)).
## Contribuições
Contribuições são bem-vindas! Se vocÊ identificar algum problema ou tiver sugestões para melhorias, por
favor abra uma *issue* ou envie um *pull request*.
