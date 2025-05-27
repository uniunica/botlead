from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
from datetime import datetime

# --- Configurações (Exemplo) ---
INSTAGRAM_USERNAME = "expansao_e_negocios"  # Colocar aqui meu nome de usuário, necessário para login
INSTAGRAM_PASSWORD = "unica2025@"    # Colocar aqui minha senha, necessário para login
TARGET_PROFILES = ['nome_perfil_faculdade1', 'nome_perfil_colegio2'] # Exemplo, lista ficará vazia para preenchimento automático posteriormente, perfis para buscar seguidores/posts
KEYWORDS = ['quero pós', 'quero fazer pós', 'quero uma pós graduação', 'interesse em pós'] # Palavras-chave para buscar nos comentários

def setup_driver():
    # Configuro o ChromeDriver automaticamente
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # Para rodar sem abrir a janela do navegador (pode ser detectado, verificar depois)
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # Evitar detecção (ainda assim, não é garantido, verificar depois)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=service, options=options)
    return driver

def login_instagram(driver, username, password):
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5) # Esperar a página carregar

    try:
        # Aceitar cookies se o botão aparecer
        cookie_button = driver.find_element(By.XPATH, "//button[text()='Permitir cookies essenciais e opcionais']")
        if cookie_button:
            cookie_button.click()
            time.sleep(2)
    except:
        print("Botão de cookie não encontrado ou já aceito.")

    user_field = driver.find_element(By.NAME, 'username')
    pass_field = driver.find_element(By.NAME, 'password')

    user_field.send_keys(username)
    pass_field.send_keys(password)
    pass_field.send_keys(Keys.RETURN)
    time.sleep(10) # Esperar o login e possível carregamento da home

    # Verificar se o login foi bem-sucedido (ex: checando a URL ou um elemento da home)
    if "accounts/login" in driver.current_url:
        print("Falha no login. Verifique as credenciais ou CAPTCHA.")
        # Adicionar tratamento de erro de login (CAPTCHA, 2FA, etc.)
        return False
    print("Login bem-sucedido!")
    return True

def get_comments_from_post(driver, post_url, keywords):
    """
    Função MUITO simplificada para pegar comentários de um post.
    Na prática, precisa rolar para carregar mais comentários,
    lidar com diferentes estruturas de HTML, etc.
    """
    driver.get(post_url)
    time.sleep(5) # Esperar comentários carregarem
    leads_from_post = []

    # Lógica para rolar e carregar todos os comentários (complexa e omitida aqui)
    # ...

    try:
        # Exemplo de seletor (PODE MUDAR E QUEBRAR FACILMENTE, aprimorar depois)
        # Este seletor é apenas ilustrativo e provavelmente não funcionará ou será instável, vou ter que aprimorar.
        # Vou precisar inspecionar o HTML do Instagram para encontrar os seletores corretos, aprimorar depois.
        comment_elements = driver.find_elements(By.XPATH, "//ul//div[@role='button']/../../..//span/a") # Exemplo muito genérico, especificar depois
        comment_texts = driver.find_elements(By.XPATH, "//ul//div[@role='button']/../../..//span[not(a)]") # Exemplo muito genérico, especificar depois
        # O seletor acima é um exemplo e provavelmente não funcionará, precisa ser ajustado

        for i in range(min(len(comment_elements), len(comment_texts))):
            user_element = comment_elements[i]
            text_element = comment_texts[i]
            username = user_element.text
            message = text_element.text.lower()
            profile_url = f"https://instagram.com/{username}"

            if any(keyword in message for keyword in keywords):
                leads_from_post.append({
                    'Nome': username,
                    'Mensagem': text_element.text, # Mensagem original
                    'Data': 'N/A com este método simples', # Difícil de pegar sem estrutura complexa, aprimorar depois
                    'Perfil': profile_url,
                    'Fonte_Post': post_url
                })
    except Exception as e:
        print(f"Erro ao tentar extrair comentários de {post_url}: {e}")

    return leads_from_post

def get_followers_from_profile(driver, profile_username):
    """
    Função MUITO simplificada para pegar seguidores.
    Precisa abrir o modal de seguidores, rolar extensivamente.
    Altamente propenso a bloqueios.
    """
    driver.get(f"https://www.instagram.com/{profile_username}/")
    time.sleep(5)
    followers_found = []

    try:
        # Clicar no link de seguidores para abrir o modal
        # O seletor XPATH aqui é um exemplo e precisa ser atualizado
        # Ex: driver.find_element(By.XPATH, f"//a[contains(@href, '/{profile_username}/followers/')]").click()
        # Ou, se for um texto:
        followers_link = driver.find_element(By.PARTIAL_LINK_TEXT, 'seguidores')
        followers_link.click()
        time.sleep(3)

        # Lógica para rolar dentro do modal de seguidores (complexa e omitida)
        # Vou precisar selecionar o elemento do modal e enviar PageDown ou executar JS para rolar
        # Exemplo (MUITO SIMPLIFICADO):
        # modal_body = driver.find_element(By.XPATH, "//div[@role='dialog']//ul") # Seletor do modal
        # for _ in range(10): # Rolar algumas vezes
        #     driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", modal_body)
        #     time.sleep(2)

        # Extrair nomes de usuário (seletor de exemplo, PODE MUDAR)
        # follower_elements = driver.find_elements(By.XPATH, "//div[@role='dialog']//a[contains(@href, '/')]") # Exemplo
        # for el in follower_elements:
        #     username = el.get_attribute('href').split('/')[-2] # Extrai username da URL do perfil
        #     if username and username != profile_username: # Evitar o próprio perfil ou links vazios
        #         followers_found.append({'Nome': username, 'Perfil': el.get_attribute('href')})
        print(f"Extração de seguidores para {profile_username} é complexa e requer rolagem no modal. Esta função é um placeholder.")

    except Exception as e:
        print(f"Erro ao tentar obter seguidores de {profile_username}: {e}")
    return followers_found


def save_leads_to_csv(leads, filename='leads_instagram'):
    if not leads:
        print("Nenhum lead encontrado para salvar.")
        return

    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_with_timestamp = f"{filename}_{now}.csv"

    # Garantir que todas as chaves estão presentes em todos os dicionários
    # e obter todas as chaves possíveis.
    all_keys = set()
    for lead in leads:
        all_keys.update(lead.keys())
    fieldnames = sorted(list(all_keys)) # Ordenar para consistência

    with open(filename_with_timestamp, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(leads)
    print(f"Arquivo salvo: {filename_with_timestamp}")


# --- Fluxo Principal (Exemplo) ---
if __name__ == "__main__":
    all_leads = []
    driver = setup_driver()

    if login_instagram(driver, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
        # Exemplo 1: Buscar por posts de um perfil e analisar comentários
        # Vou precisar primeiro obter as URLs dos posts de TARGET_PROFILES
        # Esta parte é complexa: navegar no perfil, rolar para carregar posts, extrair URLs
        print("Lógica para obter URLs de posts de perfis alvo não implementada.")
        # Exemplo manual de URL de post:
        # sample_post_url = "https://www.instagram.com/p/Cxyz123AbCd/" # SUBSTITUA PELA URL REAL DE UM POST
        # print(f"Analisando comentários do post: {sample_post_url}")
        # comments_leads = get_comments_from_post(driver, sample_post_url, KEYWORDS)
        # all_leads.extend(comments_leads)

        # Exemplo 2: Buscar seguidores de perfis alvo
        # Esta abordagem é menos direta para encontrar leads baseados em keywords,
        # a menos que depois visite o perfil de cada seguidor e analise seus posts/bio.
        # O que é ainda mais complexo e propenso a bloqueios.
        for profile_name in TARGET_PROFILES:
            print(f"\nTentando analisar o perfil: {profile_name}")
            # Para encontrar leads por seguidores, normalmente pegaria os seguidores
            # e depois, talvez, analisaria a bio de cada um ou seus posts recentes (muito intensivo)
            # Aqui, apenas listamos os seguidores como exemplo:
            # followers = get_followers_from_profile(driver, profile_name)
            # if followers:
            #     print(f"Encontrados {len(followers)} seguidores para {profile_name} (lista parcial).")
            #     # Aqui eu poderia adicionar lógica para visitar o perfil de cada seguidor
            #     # e procurar por keywords na bio ou posts, o que é muito mais trabalho.
            #     # Por agora, vamos supor que o próprio fato de seguir já é um lead (simplificação):
            #     for follower in followers:
            #         all_leads.append({
            #             'Nome': follower['Nome'],
            #             'Mensagem': f"Segue {profile_name}",
            #             'Data': 'N/A',
            #             'Perfil': follower['Perfil'],
            #             'Fonte_Perfil_Seguido': profile_name
            #         })
            print(f"A busca por seguidores e análise de seus perfis é complexa e propensa a bloqueios.")
            print(f"Alternativamente, você pode focar em posts populares de {profile_name} e analisar seus comentários.")
            # Vou precisar de uma função para encontrar posts populares/recentes de um perfil.
            # Exemplo: get_posts_from_profile(driver, profile_name) -> lista de post_urls
            # E então iterar:
            # for post_url in post_urls_from_target:
            #     comment_leads = get_comments_from_post(driver, post_url, KEYWORDS)
            #     all_leads.extend(comment_leads)
            #     time.sleep(random.uniform(5,15)) # Pausas mais longas entre ações

        if all_leads:
            save_leads_to_csv(all_leads)
        else:
            print("Nenhum lead coletado.")

    else:
        print("Não foi possível fazer login. O script não pode continuar.")

    print("Fechando o navegador...")
    time.sleep(5)
    driver.quit()