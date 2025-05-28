from selenium import webdriver # Importa o webdriver do Selenium
from selenium.webdriver.common.by import By # Importa os tipos de localização de elementos
from selenium.webdriver.chrome.options import Options # Importa opções do Chrome para configuração do navegador
from selenium.webdriver.support.ui import WebDriverWait # Importa WebDriverWait para esperar por elementos
from selenium.webdriver.support import expected_conditions as EC # Importa condições esperadas para verificar elementos
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException # Importa exceções comuns do Selenium
import time # Importa a biblioteca de tempo para simular pausas
import random # Importa a biblioteca random para gerar números aleatórios
import csv # Importa a biblioteca csv para manipulação de arquivos CSV
import os # Importa a biblioteca os para manipulação de caminhos e diretórios
import logging # Importa a biblioteca logging para registrar eventos e erros

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configurações Iniciais ---
INSTAGRAM_USERNAME = "expansao_e_negocios" # Dados de Login para preencher automaticamente
INSTAGRAM_PASSWORD = "unica2025@" # Dados de Senha para preencher automaticamente
HEADLESS_MODE = False # Mude para False para ver o navegador em ação (me ajuda no debug)
POSTS_A_ANALISAR = 9 # Quantidade de posts a analisar por hashtag (ajuste conforme necessário)

# --- Funções Auxiliares ---
def setup_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument('--headless') # Executa o Chrome em modo headless (sem interface gráfica)
    options.add_argument('--disable-gpu') # Desativa a GPU para evitar problemas em alguns sistemas
    options.add_argument('--no-sandbox') # Necessário para rodar em alguns ambientes como servidores
    options.add_argument('--disable-dev-shm-usage') # Necessário para evitar problemas de memória em containers
    options.add_argument('--lang=pt-BR') # Definir idioma para consistência de seletores de texto
    options.add_experimental_option('prefs', {'intl.accept_languages': 'pt-BR'})
    driver = webdriver.Chrome(options=options) # Inicializa o driver do Chrome com as opções definidas
    driver.set_window_size(1280, 800) # Tamanho de janela pode influenciar o layout
    return driver # Configura o driver do Selenium para o Chrome

# Função para simular tempo humano (pausas aleatórias)
def simular_tempo_humano(min_s=2, max_s=5):
    time.sleep(random.uniform(min_s, max_s))

# --- Funções Principais (Refatoradas) ---

def login_instagram(driver, username, password):
    if not username or not password:
        logging.warning("Nome de usuário ou senha não fornecidos. Prosseguindo sem login.")
        return False

    logging.info("Tentando fazer login...")
    driver.get("https://www.instagram.com/accounts/login/")
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username")) # Espera o campo de nome de usuário estar presente
        )
        driver.find_element(By.NAME, "username").send_keys(username) # Preenche o campo de nome de usuário
        driver.find_element(By.NAME, "password").send_keys(password) # Preenche o campo de senha
        driver.find_element(By.XPATH, "//button[@type='submit']").click() # Clica no botão de login
        simular_tempo_humano(5, 7) # Esperar o login processar

        # Verificar se o login foi bem-sucedido (ex: checando se o popup de "Salvar informações" aparece)
        # ou se o ícone do perfil está visível
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/{}/')]".format(username.lower()))) # Verifica se o perfil do usuário está acessível
        )
        logging.info("Login bem-sucedido!")
        # Lidar com popups pós-login (Salvar informações, Ativar notificações)
        try:
            # Botão "Agora não" para salvar informações de login
            not_now_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='Agora não'] | //div[@role='button' and text()='Agora não']"))
            )
            not_now_button.click()
            logging.info("Popup 'Salvar informações' dispensado.")
            simular_tempo_humano(2,3)
        except TimeoutException:
            logging.info("Nenhum popup 'Salvar informações' encontrado ou já dispensado.")

        try:
            # Botão "Agora não" para ativar notificações
            notifications_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='Agora não'] | //button[contains(.,'Not Now')]"))
            )
            notifications_button.click()
            logging.info("Popup 'Ativar notificações' dispensado.")
            simular_tempo_humano(2,3)
        except TimeoutException:
            logging.info("Nenhum popup 'Ativar notificações' encontrado ou já dispensado.")

        return True
    except TimeoutException:
        logging.error("Falha no login: Timeout ao esperar elementos da página de login ou pós-login.")
        return False
    except Exception as e:
        logging.error(f"Erro inesperado durante o login: {e}")
        return False

# Função para coletar links de posts recentes de uma hashtag
def coletar_links_de_posts_recentes(driver, hashtag, quantidade_posts):
    logging.info(f"Navegando para a página da hashtag: {hashtag}")
    base_url = f"https://www.instagram.com/explore/tags/{hashtag}/" # URL base para a hashtag
    driver.get(base_url)
    # É crucial dar tempo suficiente para a página carregar, especialmente a grade de posts.
    simular_tempo_humano(5, 8) # Aumentar um pouco a simulação de tempo inicial

    post_links = []
    tentativas_scroll = 0
    max_tentativas = 10

    while len(post_links) < quantidade_posts and tentativas_scroll < max_tentativas:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        simular_tempo_humano(2, 4)

        post_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') and @role='link']")
        tentativas_scroll += 1

    logging.info(f"Encontrados {len(post_links)} posts após {tentativas_scroll} scrolls.")

    try:
        # Esperar pelos links de posts
        posts_xpath = "//a[contains(@href, '/p/') and @role='link']"
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.XPATH, posts_xpath))
        )

        post_links = driver.find_elements(By.XPATH, posts_xpath)
        logging.info(f"Encontrados {len(post_links)} posts potenciais.")

        todos_comentaristas = set()

        abertos = 0
        for i, link in enumerate(post_links):
            if abertos >= quantidade_posts:
                break

            try:
                # Rolar até o elemento para garantir visibilidade
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                simular_tempo_humano(1, 2)

                # Clicar no link para abrir o modal
                link.click()
                logging.info(f"Modal do post {i+1} aberto.")
                abertos += 1

                # Tempo para visualizar/modal carregar
                simular_tempo_humano(3, 5)

                coments = extrair_comentaristas_do_modal(driver)
                todos_comentaristas.update(coments)
                logging.info(f"Post {i+1}: {len(coments)} comentaristas coletados.")

                # Fechar o modal (opcional)
                close_button_xpath = "//button[@aria-label='Fechar' or @aria-label='Close']"
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, close_button_xpath))
                ).click()

                simular_tempo_humano(1, 2)  # Pausa entre modais

            except ElementClickInterceptedException:
                logging.warning(f"Elemento {i+1} bloqueado por overlay. Pulando...")
            except Exception as e:
                logging.error(f"Erro ao abrir modal do post {i+1}: {e}")

    except TimeoutException:
        logging.error("Timeout ao aguardar carregamento dos posts.")

    return todos_comentaristas

# Função para extrair comentaristas de um post específico
def extrair_comentaristas_do_modal(driver):
    try:
        # Esperar até que os comentários estejam visíveis
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//ul//a[contains(@href, '/') and starts-with(@href, '/') and not(contains(@href, '/p/'))]"))
        )

        # Selecionar todos os links que apontam para perfis (excluindo links de posts, stories, etc.)
        comentaristas = driver.find_elements(By.XPATH, "//ul//a[contains(@href, '/') and starts-with(@href, '/') and not(contains(@href, '/p/'))]")

        nomes = set()
        for el in comentaristas:
            href = el.get_attribute("href")
            # Extrair nome do usuário da URL (ex: https://instagram.com/nome -> nome)
            if href and "instagram.com/" in href:
                nome = href.split("instagram.com/")[-1].replace("/", "")
                if nome not in ["", "explore", "reels"]:  # Ignora links genéricos
                    nomes.add(nome)

        return nomes

    except TimeoutException:
        logging.warning("Timeout ao tentar encontrar os comentaristas no modal.")
        return set()
    except Exception as e:
        logging.error(f"Erro ao extrair comentaristas: {e}")
        return set()


# Função para salvar os comentaristas em um arquivo CSV
def salvar_comentaristas_csv(comentaristas_por_post, nome_arquivo='comentaristas_instagram.csv'):
    logging.info(f"Salvando dados no arquivo: {nome_arquivo}")
    caminho_base = 'static/leads' # Diretório base para salvar os arquivos
    if not os.path.exists(caminho_base):
        os.makedirs(caminho_base)
        logging.info(f"Diretório '{caminho_base}' criado.")

    caminho_completo = os.path.join(caminho_base, nome_arquivo)

    with open(caminho_completo, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Nome de Usuário Comentador', 'Post de Origem'])
        for post_url, usuarios in comentaristas_por_post.items():
            for usuario in usuarios:
                writer.writerow([usuario, post_url])
    logging.info(f"Dados salvos com sucesso em {caminho_completo}")
    return caminho_completo

# --- Bloco de Execução Principal ---
if __name__ == "__main__":
    driver = None # Inicializa driver como None
    try:
        driver = setup_driver(headless=HEADLESS_MODE)

        # Opcional: Tentar login
        if INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD:
            if not login_instagram(driver, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
                logging.warning("Login falhou ou não foi tentado. Algumas funcionalidades podem ser limitadas.")
        else:
            logging.info("Nenhuma credencial fornecida, prosseguindo sem login.")
            # Acessar uma página do Instagram para aceitar cookies se necessário (sem login)
            driver.get("https://www.instagram.com/")
            simular_tempo_humano(3,5)
            try:
                # Seletor para o botão de aceitar cookies (o texto/seletor pode variar)
                accept_cookies_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Permitir todos os cookies'] | //button[text()='Allow all cookies'] | //button[contains(text(),'Permitir cookies')]"))
                )
                accept_cookies_button.click()
                logging.info("Cookies aceitos.")
                simular_tempo_humano(2,3)
            except TimeoutException:
                logging.info("Nenhum popup de cookies encontrado ou já aceito.")

        hashtag_alvo = 'posgraduacao' # Sua hashtag aqui
        links_posts_recentes = coletar_links_de_posts_recentes(driver, hashtag_alvo, POSTS_A_ANALISAR)

        if not links_posts_recentes:
            logging.warning("Nenhum link de post foi coletado. Encerrando.")
        else:
            todos_comentaristas_por_post = {}
            for link_post in links_posts_recentes:
                comentaristas_do_post = extrair_comentaristas_do_modal(driver)
                if comentaristas_do_post: # Apenas adiciona se houver comentaristas
                    todos_comentaristas_por_post[link_post] = comentaristas_do_post
                simular_tempo_humano(3, 6) # Pausa entre análise de posts

            if todos_comentaristas_por_post:
                caminho_salvo = salvar_comentaristas_csv(todos_comentaristas_por_post)
                logging.info(f"✅ Processo concluído. Comentaristas salvos em: {caminho_salvo}")
            else:
                logging.info("Nenhum comentarista encontrado nos posts analisados.")

    except Exception as e:
        logging.critical(f"Ocorreu um erro crítico no script: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")