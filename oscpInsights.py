import os
import praw
import openai
from datetime import datetime, timezone
import logging
import sqlite3

def setup_logging():
    """
    Configura o logging para o script.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_api_keys():
    """
    Carrega as API keys a partir das variáveis de ambiente.
    """
    CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    USER_AGENT = os.getenv("REDDIT_USER_AGENT")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not all([CLIENT_ID, CLIENT_SECRET, USER_AGENT, OPENAI_API_KEY]):
        raise ValueError("❌ Missing API keys! Make sure all API keys are set as environment variables.")
    return CLIENT_ID, CLIENT_SECRET, USER_AGENT, OPENAI_API_KEY

def initialize_reddit(client_id, client_secret, user_agent):
    """
    Inicializa a API do Reddit utilizando a biblioteca PRAW.
    """
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )

def setup_database(db_file="oscp_posts.db"):
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

def is_useful_post(post):
    """
    Filtra posts que são detalhados e úteis para preparação do OSCP.
    """
    content = f"{post.title} {post.selftext}".lower()
    useful_keywords = [
        "study", "methodology", "privilege escalation", "active directory",
        "tools", "practice", "proving grounds", "htb", "time management",
        "exam strategy", "report writing", "buffer overflow", "initial foothold"
    ]
    return any(keyword in content for keyword in useful_keywords) and len(post.selftext) > 700

def collect_posts(subreddit, search_query, start_date, end_date):
    """
    Coleta posts do subreddit que atendem aos critérios de data e utilidade.
    """
    posts = []
    for post in subreddit.search(search_query, sort="new", time_filter="all"):
        post_timestamp = post.created_utc
        if start_date <= post_timestamp <= end_date and is_useful_post(post):
            posts.append(post)
    return posts

def save_posts_to_db(conn, posts):
    """
    Salva os posts e seus comentários no banco de dados SQLite.
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
        
        # Carregar e salvar todos os comentários do post
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

def analyze_oscp_success(posts_text):
    """
    Utiliza a API do OpenAI para analisar o texto dos posts coletados, extraindo insights acionáveis.
    """
    prompt = f"""
    Você está analisando histórias de sucesso do OSCP de alta qualidade. Seu objetivo é extrair **insights detalhados e acionáveis** 
    para futuros estudantes, com base em técnicas reais de estudo, ferramentas e estratégias que funcionaram com eficiência e sagacidade.

    **Foque em:**
    - **Ambientes de prática:** HTB, Proving Grounds, laboratórios caseiros, boxes do OSCP aposentadas.
    - **Técnicas de enumeração:** Portas, serviços, usuários, compartilhamentos.
    - **Estratégias de escalonamento de privilégios:** Misconfigurações em Windows e Linux, exploits de kernel.
    - **Ataques a Active Directory:** Kerberoasting, ASREPRoasting, análise com BloodHound.
    - **Erros comuns e como foram superados.**
    - **Dicas de gerenciamento de tempo durante o exame.**
    - **Estratégias de exame para boxes AD e standalone.**
    - **Técnicas eficazes de escrita de relatórios.**

    **Estruture sua resposta assim:**

    1️⃣ **Estratégia Principal (por exemplo, Foco em Active Directory)**
    - 🔹 **Recursos Recomendados:** (por exemplo, série do Derron C no YouTube, TryHackMe, HackTheBox Pro Labs)
    - 🔹 **Ferramenta Utilizada:** (por exemplo, `BloodHound`, `CrackMapExec`, `Mimikatz`)
    - 🔹 **Estratégia:** (por exemplo, "Estudantes praticaram construir caminhos de ataque utilizando BloodHound e CrackMapExec.")
    - 🔹 **Exemplo:** ("Um candidato obteve acesso inicial usando ASREPRoasting e se moveu lateralmente com Pass-The-Hash.")

    **Extraia exatamente 10 técnicas ou práticas de estudo que aparecem com maior frequência.**

    **Dados:** 
    {posts_text}
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",  # Utilize "gpt-3.5-turbo" se ocorrerem problemas de rate limit
            messages=[
                {"role": "system", "content": "Você é um mentor de cibersegurança ofensiva com 15 anos de experiência prática em exploitation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"Erro na análise com OpenAI: {e}")
        return "Erro na análise com OpenAI."

def main():
    setup_logging()
    
    # Carrega e configura as API keys
    CLIENT_ID, CLIENT_SECRET, USER_AGENT, OPENAI_API_KEY = load_api_keys()
    openai.api_key = OPENAI_API_KEY

    # Inicializa a API do Reddit
    reddit = initialize_reddit(CLIENT_ID, CLIENT_SECRET, USER_AGENT)
    subreddit = reddit.subreddit("oscp")

    # Define o intervalo de datas (2023 e 2024)
    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()
    end_date = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc).timestamp()

    # Define a query de busca conforme o código original ("passed")
    search_query = "passed"

    logging.info("Coletando posts...")
    posts = collect_posts(subreddit, search_query, start_date, end_date)
    logging.info(f"Coletados {len(posts)} posts úteis.")

    # Configura o banco de dados SQLite e salva posts e comentários
    conn = setup_database("oscp_posts.db")
    logging.info("Salvando posts e comentários no banco de dados SQLite...")
    save_posts_to_db(conn, posts)
    logging.info("Dados salvos no banco de dados SQLite.")

    # Preparar o texto para a análise (incluindo posts e comentários)
    post_texts = []
    for post in posts:
        post_info = f"Title: {post.title}\nBody: {post.selftext}\nURL: {post.url}\n"
        post_texts.append(post_info)
        try:
            post.comments.replace_more(limit=0)
            for comment in post.comments.list():
                comment_info = f"Reply: {comment.body}\n\n"
                post_texts.append(comment_info)
        except Exception as e:
            logging.error(f"Erro ao coletar comentários do post {post.id}: {e}")

    full_text = "\n".join(post_texts)[:5000]
    logging.info("Analisando posts com IA...")
    oscp_analysis = analyze_oscp_success(full_text)

    # Salva os resultados da análise em um arquivo de texto
    ai_output_file = "oscp_success_analysis.txt"
    with open(ai_output_file, "w", encoding="utf-8") as f:
        f.write(oscp_analysis)
    logging.info(f"Análise de IA concluída. Confira '{ai_output_file}' para os resultados.")

if __name__ == '__main__':
    main()
