from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
import csv
import os
import logging

# Configurar navegador
options = Options()
options.add_argument('--headless')  # modo invisível
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)

# Função para simular tempo de espera entre ações
def simular_tempo(min_s=2, max_s=5):
    time.sleep(random.uniform(min_s, max_s))

# Função para buscar perfis por hashtag
def buscar_perfis_por_hashtag(hashtag, limite=10):
    base_url = f"https://www.instagram.com/explore/tags/{hashtag}/"
    driver.get(base_url)
    simular_tempo(4, 6)

    perfis_encontrados = set()
    links_visitados = set()

    # Scroll e coleta
    while len(perfis_encontrados) < limite:
        # Encontrar todos os links dos posts
        posts = driver.find_elements(By.TAG_NAME, 'a')
        post_links = [p.get_attribute('href') for p in posts if '/p/' in p.get_attribute('href')]

        for link in post_links:
            if link not in links_visitados:
                driver.get(link)
                simular_tempo(2, 4)
                try:
                    perfil = driver.find_element(By.XPATH, '//a[contains(@href, "/") and @class]').get_attribute('href')
                    perfis_encontrados.add(perfil)
                    links_visitados.add(link)
                except:
                    continue
                if len(perfis_encontrados) >= limite:
                    break

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        simular_tempo(3, 6)

    return list(perfis_encontrados)

# Função para extrair informações do perfil
def extrair_info_perfil(perfil_url):
    driver.get(perfil_url)
    simular_tempo(2, 4)
    try:
        nome_usuario = perfil_url.strip('/').split('/')[-1]
        bio_element = driver.find_element(By.XPATH, '//div[@class="_aa_c"]/div/span')
        bio = bio_element.text
    except:
        bio = ""
        nome_usuario = perfil_url.strip('/').split('/')[-1]
    return nome_usuario, perfil_url, bio

# Função para buscar perfis e salvar em CSV
def salvar_csv(dados, nome_arquivo='leads_instagram.csv'):
    caminho = os.path.join('static', 'leads')
    os.makedirs(caminho, exist_ok=True)
    caminho_arquivo = os.path.join(caminho, nome_arquivo)

    with open(caminho_arquivo, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Nome de Usuário', 'URL do Perfil', 'Bio'])
        writer.writerows(dados)

    return nome_arquivo

# Exemplo de uso
if __name__ == "__main__":
    hashtag = 'posgraduacao'
    limite = 5

    print(f"🔍 Buscando perfis com #{hashtag}...")
    perfis = buscar_perfis_por_hashtag(hashtag, limite=limite)

    dados_leads = []
    for url in perfis:
        print(f"📄 Extraindo dados de: {url}")
        nome, link, bio = extrair_info_perfil(url)
        dados_leads.append([nome, link, bio])

    arquivo_gerado = salvar_csv(dados_leads)
    print(f"✅ Leads salvos em: static/leads/{arquivo_gerado}")

    driver.quit()
