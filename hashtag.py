from selenium import webdriver # Importa o webdriver do Selenium
from selenium.webdriver.common.by import By # Importa os tipos de localização de elementos
from selenium.webdriver.chrome.options import Options # Importa opções do Chrome para configuração do navegador
from selenium.webdriver.support.ui import WebDriverWait # Importa WebDriverWait para esperar por elementos
from selenium.webdriver.support import expected_conditions as EC # Importa condições esperadas para verificar elementos
from selenium.common.exceptions import TimeoutException, NoSuchElementException # Importa exceções comuns do Selenium
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

    # --- PAUSA PARA DEBUG MANUAL (descomente se precisar inspecionar) ---
    # logging.info("PÁGINA DA HASHTAG CARREGADA. Verifique o layout e os seletores.")
    # input(">>> Pressione Enter no console para tentar coletar os links dos posts...")
    # --------------------------------------------------------------------

    # Tentativa de scroll inicial para ajudar a carregar elementos que podem estar "lazy-loaded"
    try:
        logging.info("Realizando scroll inicial na página da hashtag...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight*0.35);") # Scroll para baixo para carregar mais posts
        simular_tempo_humano(1, 3)
        driver.execute_script("window.scrollTo(0, 0);") # Opcional: voltar ao topo
        simular_tempo_humano(1, 2)
    except Exception as e_scroll:
        logging.warning(f"Erro durante scroll inicial: {e_scroll}")

    links_posts = set()

    try:
        # NOVO SELETOR XPath:
        # 1. Encontra todas as <div class="_aagw">.
        # 2. Dentro de cada uma dessas divs, encontra o link <a> que contém '/p/' em seu href.
        # Este XPath assume que o link <a> é um descendente direto ou indireto da div._aagw.
        post_links_xpath = "//div[@class='_aagw']//a[contains(@href, '/p/')]"

        # Se a classe _aagw for do próprio link <a> (menos provável pela sua descrição):
        # post_links_xpath = "//a[@class='_aagw' and contains(@href, '/p/')]"

        logging.info(f"Tentando encontrar links de posts com o seletor: {post_links_xpath}")

        # Aumentar o tempo de espera para garantir que os elementos tenham chance de carregar,
        # especialmente se a conexão for lenta ou a página for pesada.
        WebDriverWait(driver, 25).until(
            EC.presence_of_all_elements_located((By.XPATH, post_links_xpath))
        )

        # Coleta os elementos <a> que são os links para os posts
        post_link_elements = driver.find_elements(By.XPATH, post_links_xpath)
        logging.info(f"Número de elementos de link de post encontrados com o seletor principal: {len(post_link_elements)}")

        if not post_link_elements:
            logging.warning("Nenhum elemento de link de post encontrado com o seletor principal. Isso pode indicar que o seletor está desatualizado ou a página não carregou como esperado.")
            # Tentativa de um seletor de fallback mais genérico para diagnóstico (pode ser menos preciso)
            fallback_xpath = "//article//a[contains(@href, '/p/')]" # Um seletor comum de posts dentro de <article>
            logging.info(f"Tentando seletor de fallback: {fallback_xpath}")
            try:
                post_link_elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, fallback_xpath))
                )
                logging.info(f"Com seletor de fallback, encontrados {len(post_link_elements)} elementos.")
            except TimeoutException:
                logging.warning("Seletor de fallback também não encontrou elementos. A estrutura da página pode ter mudado significativamente.")
                return [] # Retorna lista vazia se nada for encontrado

        # Itera sobre os elementos encontrados e extrai os links
        for link_element in post_link_elements:
            if len(links_posts) >= quantidade_posts:
                break # Já coletamos a quantidade desejada
            try:
                link = link_element.get_attribute('href')
                if link and '/p/' in link: # Confirma que é um link de post
                    links_posts.add(link)
                    logging.debug(f"Link de post adicionado: {link}")
                else:
                    logging.debug(f"Elemento encontrado com href inválido ou não é link de post: {link}")
            except Exception as e_attr:
                # Isso pode acontecer se o elemento se tornar "stale"
                logging.warning(f"Erro ao obter href de um link_element: {e_attr}")

        if not links_posts:
            logging.warning("Nenhum link de post válido foi adicionado ao set após a iteração.")
        else:
            logging.info(f"Coletados {len(links_posts)} links de posts únicos.")

        return list(links_posts)[:quantidade_posts] # Garante o limite exato, mesmo que mais tenham sido encontrados

    except TimeoutException:
        logging.error(f"Timeout final ao esperar os posts na página da hashtag com o seletor: {post_links_xpath}. A página pode não ter carregado os posts esperados ou o seletor está incorreto.")
        return []
    except Exception as e:
        logging.error(f"Erro geral e inesperado ao coletar links de posts: {e}", exc_info=True)
        return []

# Função para extrair comentaristas de um post específico
def extrair_comentaristas_do_post(driver, post_url):
    logging.info(f"Acessando post: {post_url}")
    driver.get(post_url)
    comentaristas = set()
    try:
        # Esperar a seção de comentários ou o botão de "ver comentários"
        # Seletor para o botão "Ver todos os X comentários" - PODE MUDAR!
        # Tenta clicar para expandir comentários se o botão existir
        try:
            view_comments_button_xpath = "//button[contains(span/text(),'Ver todos os comentários') or contains(span/text(), 'View all comments')]"
            view_comments_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, view_comments_button_xpath))
            )
            view_comments_button.click()
            logging.info("Botão 'Ver todos os comentários' clicado.")
            simular_tempo_humano(2, 4) # Esperar comentários carregarem após clique
        except TimeoutException:
            logging.info("Botão 'Ver todos os comentários' não encontrado ou não clicável. Tentando ler comentários diretamente.")

        # Tentar rolar para carregar mais comentários ou clicar em "carregar mais"
        # Esta parte é a mais complexa e sujeita a mudanças no Instagram
        last_height = driver.execute_script("return document.body.scrollHeight")
        patience = 5 # Número de tentativas de scroll sem novos comentários antes de parar
        patience_counter = 0

        while patience_counter < patience:
            # Seletor para usernames dos comentaristas - PODE MUDAR MUITO!
            # Geralmente, o nome do usuário está dentro de um <a> com um atributo específico ou classe.
            # Exemplo de XPath (altamente propenso a quebrar):
            # //ul//div[@role='button']/../../div[1]/div[1]/div/span/a (este é complexo e antigo)
            # Mais comum: dentro de uma lista <ul>, cada <li> é um comentário.
            # O primeiro link <a> dentro da estrutura do comentário costuma ser o usuário.
            # Exemplo: "//div[contains(@class, '_a9zr')]//a[contains(@class, 'notranslate')]"
            # Ou: "//ul//li//a[starts-with(@href, '/') and not(contains(@href, '/p/')) and not(contains(@href, '/tags/'))]"
            # É FUNDAMENTAL INSPECIONAR O HTML NO MOMENTO DO USO PARA ACHAR O SELETOR CORRETO

            # Seletor focado em encontrar links de perfil dentro da área de comentários
            # Este seletor tenta ser um pouco mais genérico, mas ainda pode falhar.
            # O ideal seria um seletor que identifique a lista de comentários e depois os links de usuário dentro dela.
            commenter_elements_xpath = "//article//div[contains(@class,'EtaWk')]//ul//li//div[contains(@class,'C4VMK')]//a[contains(@class,'sqdOP')]"
            # O XPATH ACIMA É UM EXEMPLO GENÉRICO E ANTIGO, PROVAVELMENTE NÃO FUNCIONARÁ.
            # DEVO INSPECIONAR O ELEMENTO NO NAVEGADOR E CRIAR UM XPATH NOVO.
            # Um padrão mais atualizado pode envolver classes como _a9zc, _a9zd para o comentário
            # e o link do usuário pode ser algo como:
            # "//div[contains(@class, '_a9zr')]//span/a" ou "//div[contains(@class, '_a9zr')]//a[@role='link']"
            # Para este exemplo, vou usar um seletor que busca por links de perfil no corpo do post,
            # assumindo que a área de comentários está lá.
            # Este XPath é um PALPITE e precisa ser VERIFICADO:
            commenter_links_xpath = "//article//ul//a[contains(@href, '/') and not(contains(@href, '/p/')) and string-length(normalize-space(text())) > 0]"

            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//article//ul")) # Espera a lista de comentários
                )
                # Seletor mais específico para nomes de usuário em comentários (requer inspeção constante)
                # As classes como '_a9zr' ou '_ap3a _aaco _aacw _aacx _aad7 _aade' são comuns, mas mudam.
                # Este é um exemplo genérico de como poderia ser estruturado:
                commenter_elements = driver.find_elements(By.XPATH, "//div[contains(@class, '_a9zr')]//a[@role='link']")
                if not commenter_elements: # Tentar uma alternativa se o primeiro falhar
                     commenter_elements = driver.find_elements(By.XPATH, "//ul/li//div[@role='button']/preceding-sibling::div//a")

                # Verifica se encontrou elementos de comentaristas
                for el in commenter_elements:
                    username = el.text.strip()
                    href = el.get_attribute('href')
                    # Verifica se o texto é um nome de usuário válido e o link é para um perfil
                    if username and href and f"/{username}/" in href and not "explore/tags" in href:
                        comentaristas.add(username)
            except Exception as e_inner:
                logging.warning(f"Não foi possível extrair comentaristas com o seletor principal: {e_inner}")

            # Lógica de scroll ou "carregar mais"
            # Tenta encontrar um botão "carregar mais comentários" (geralmente um ícone "+")
            try:
                load_more_button_svg_xpath = "//div[@role='button' and .//span[@aria-label='Carregar mais comentários']]" # XPath para SVG
                load_more_button = driver.find_element(By.XPATH, load_more_button_svg_xpath)
                # driver.execute_script("arguments[0].scrollIntoView();", load_more_button) # Garante que é visível
                load_more_button.click()
                logging.info("Botão 'Carregar mais comentários' (SVG) clicado.")
                simular_tempo_humano(2, 4)
                patience_counter = 0 # Reseta a paciência pois novos comentários foram carregados
                continue # Volta para tentar ler novos comentários
            except NoSuchElementException:
                logging.debug("Botão 'Carregar mais comentários' (SVG) não encontrado, tentando rolar.")
                pass # Prossegue para o scroll se o botão não for encontrado
            except Exception as e_click:
                logging.warning(f"Erro ao clicar no botão 'Carregar mais comentários' (SVG): {e_click}")
                pass

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            simular_tempo_humano(1, 2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                patience_counter += 1
                logging.debug(f"Scroll não carregou novos comentários. Tentativa {patience_counter}/{patience}")
            else:
                patience_counter = 0 # Reseta a paciência pois novos comentários foram carregados
            last_height = new_height

        logging.info(f"Encontrados {len(comentaristas)} comentaristas únicos no post {post_url}.")
        return list(comentaristas)

    except TimeoutException:
        logging.error(f"Timeout ao carregar elementos do post {post_url}.")
        return []
    except Exception as e:
        logging.error(f"Erro ao extrair comentaristas do post {post_url}: {e}")
        return []

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
                comentaristas_do_post = extrair_comentaristas_do_post(driver, link_post)
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