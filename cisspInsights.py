import os
import praw
import sqlite3
import logging
from datetime import datetime, timezone
import ollama
import re

# Biblioteca para tradução
from deep_translator import GoogleTranslator

def setup_logging():
    """
    Configura o logging para o script.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_api_keys():
    """
    Carrega as API keys a partir das variáveis de ambiente (apenas do Reddit).
    """
    CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    USER_AGENT = os.getenv("REDDIT_USER_AGENT")

    if not all([CLIENT_ID, CLIENT_SECRET, USER_AGENT]):
        raise ValueError("❌ Missing Reddit API keys! Verifique as variáveis de ambiente.")
    return CLIENT_ID, CLIENT_SECRET, USER_AGENT

def initialize_reddit(client_id, client_secret, user_agent):
    """
    Inicializa a API do Reddit utilizando a biblioteca PRAW.
    """
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )

def setup_database(db_file="cissp_posts.db"):
    """
    Configura o banco de dados SQLite e cria as tabelas necessárias para posts e comentários.
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            title TEXT,
            selftext TEXT,
            url TEXT,
            created_utc REAL
        );
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            post_id TEXT,
            comment_body TEXT,
            created_utc REAL,
            FOREIGN KEY (post_id) REFERENCES posts (id)
        );
    ''')
    conn.commit()
    return conn

def collect_posts(subreddit, search_query, limit=100):
    """
    Coleta posts do subreddit com base em um termo de busca.
    - limit define quantos resultados você quer pegar, até 100, 200 etc.
    - sort="new" para pegar os mais recentes (ou "relevance", etc.)
    - time_filter="all" para pegar de qualquer período.
    """
    posts = []
    for post in subreddit.search(search_query, sort="new", time_filter="all", limit=limit):
        posts.append(post)
    return posts

def save_posts_to_db(conn, posts):
    """
    Salva os posts e *opcionalmente* seus comentários no banco de dados SQLite.
    """
    cur = conn.cursor()
    for post in posts:
        try:
            cur.execute('''
                INSERT OR IGNORE INTO posts (id, title, selftext, url, created_utc)
                VALUES (?, ?, ?, ?, ?)
            ''', (post.id, post.title, post.selftext, post.url, post.created_utc))
        except Exception as e:
            logging.error(f"Erro ao salvar o post {post.id}: {e}")

        # Se você não quer salvar comentários, basta comentar o bloco abaixo.
        # Caso queira armazená-los no banco mas não analisá-los, deixe esse bloco.
        try:
            post.comments.replace_more(limit=0)
            for comment in post.comments.list():
                try:
                    cur.execute('''
                        INSERT OR IGNORE INTO comments (id, post_id, comment_body, created_utc)
                        VALUES (?, ?, ?, ?)
                    ''', (comment.id, post.id, comment.body, getattr(comment, 'created_utc', None)))
                except Exception as e:
                    logging.error(f"Erro ao salvar o comentário {comment.id}: {e}")
        except Exception as e:
            logging.error(f"Erro ao processar comentários do post {post.id}: {e}")

    conn.commit()

def analyze_cissp_success(posts_text):
    """
    Utiliza a biblioteca ollama para enviar o prompt ao Ollama (LLM local).
    Retorna o texto processado como resposta, focado em dicas e estratégias para CISSP.
    """
    # Instância do cliente Ollama
    client = ollama.Client()

    # Prompt "system" e "user"
    system_prompt = (
        "Você é um mentor de cibersegurança corporativa com 15 anos de experiência em segurança da informação e CISSP.\n\n"
    )

    user_prompt = f"""
Por favor, responda em PORTUGUES!

Você está analisando histórias de sucesso (ou tentativas) do CISSP de alta qualidade. Seu objetivo é extrair **insights detalhados e acionáveis** 
para futuros estudantes, baseando-se em estratégias, livros de estudo, simulados e abordagens eficazes que levaram (ou levarão) à aprovação no exame.

**Foque em:**
- **Domínios:** Os 8 domínios do CISSP (Security & Risk Management, Asset Security, Security Architecture & Engineering, etc.).
- **Materiais de estudo:** Livros (Shon Harris, Sybex), cursos (ISC2 Official, Cybrary), simulados (Boson, CCCure, etc.).
- **Estratégias de estudo e memorização:** Flashcards, resumos, grupos de estudo, gerenciadores de tempo.
- **Erros comuns e como foram superados.**
- **Técnicas de gestão de tempo durante o exame.**
- **Dicas práticas para lidar com questões complexas.**
- **Estratégias de simulado e revisão.**

**Estruture sua resposta assim:**

1️⃣ **Estratégia Principal (por exemplo, Foco em simulados)**
- 🔹 **Recursos Recomendados:** (por exemplo, "Livro da Shon Harris, Simulados Boson")
- 🔹 **Ferramenta ou Método:** (por exemplo, "Resumos em flashcards", "Aprofundar em cada domínio antes de passar para o próximo")
- 🔹 **Estratégia:** (por exemplo, "Fazer 50 questões por dia e revisar erros imediatamente.")
- 🔹 **Exemplo:** ("Um candidato percebeu que estava errando muitas perguntas em Criptografia e investiu 2 semanas a mais no domínio.")

**Extraia exatamente 10 técnicas ou práticas de estudo que aparecem com maior frequência.**

**Dados:** 
{posts_text}
"""

    final_prompt = system_prompt + user_prompt

    try:
        response = ollama.generate(
            model="deepseek-r1",  # Ajuste para o modelo que você estiver usando
            prompt=final_prompt
        )
        return response["response"]
    except Exception as e:
        logging.error(f"Erro ao gerar resposta com Ollama: {e}")
        return "Erro ao gerar resposta com Ollama."

def remove_think_blocks(text):
    """
    Remove todo conteúdo que estiver entre <think>...</think>, incluindo as tags.
    """
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

def translate_to_portuguese(text):
    """
    Traduz o texto para Português usando deep-translator.
    """
    translator = GoogleTranslator(source='auto', target='pt')
    return translator.translate(text)

def main():
    setup_logging()
    
    # Carrega as credenciais do Reddit
    CLIENT_ID, CLIENT_SECRET, USER_AGENT = load_api_keys()
    reddit = initialize_reddit(CLIENT_ID, CLIENT_SECRET, USER_AGENT)
    subreddit = reddit.subreddit("cissp")

    # Termo de busca (pode testar variações: "passed cissp", "I passed CISSP", etc.)
    search_query = "passed cissp"

    logging.info("Coletando posts...")
    posts = collect_posts(subreddit, search_query, limit=100)
    logging.info(f"Coletados {len(posts)} posts.")

    # Configura o banco de dados SQLite e salva posts e comentários
    conn = setup_database("cissp_posts.db")
    logging.info("Salvando posts e comentários no banco de dados SQLite...")
    save_posts_to_db(conn, posts)
    logging.info("Dados salvos no banco de dados SQLite.")

    # ======== AQUI: montar texto APENAS DOS POSTS (sem comentários) ========
    post_texts = []
    for post in posts:
        # Criamos somente um resumo do post: titulo, corpo e url
        post_info = f"Title: {post.title}\nBody: {post.selftext}\nURL: {post.url}\n"
        post_texts.append(post_info)

    # Juntar todo o texto em uma só string (cuidado com tamanho!)
    full_text = "\n".join(post_texts)

    # Se estiver muito grande, você pode limitar ou usar um método de "chunking"
    # mas, para demonstração, vamos enviar tudo:
    # full_text = full_text[:25000]  # Caso queira limitar

    logging.info("Analisando posts com IA (Ollama)...")
    cissp_analysis = analyze_cissp_success(full_text)

    # Remove blocos <think> (caso existam)
    cissp_analysis = remove_think_blocks(cissp_analysis)

    # Tradução final para PT (caso o LLM responda em inglês ou mesclado)
    cissp_analysis = translate_to_portuguese(cissp_analysis)

    # Salvar análise em arquivo
    ai_output_file = "cissp_success_analysis.txt"
    with open(ai_output_file, "w", encoding="utf-8") as f:
        f.write(cissp_analysis)

    logging.info(f"Análise de IA concluída. Confira '{ai_output_file}' para os resultados.")

if __name__ == '__main__':
    main()