import requests
from bs4 import BeautifulSoup
import re
from time import sleep
from googlesearch import search  # Importa a função search
import csv
import sys

# --- Configurações Iniciais ---
# Lista de palavras-chave para busca!
QUERIES = [
    "escola tecnica campinas",
]

# Número de resultados do Google para processar por query
NUM_RESULTS_PER_QUERY = 10

# Delay entre requisições para não sobrecarregar os servidores (em segundos)
REQUEST_DELAY = 2

# Expressões regulares para extrair informações
# Esta regex para email é básica. Precisa ser aprimorada.
EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
# Esta regex para telefone brasileiro é simplificada.
# Usar formatos como (XX) XXXX-XXXX, (XX) XXXXX-XXXX, XX XXXXXXXX, etc.
PHONE_REGEX = r"\(?\b\d{2}\b\)?\s?\b\d{4,5}\b-?\b\d{4}\b"

# --- Funções Auxiliares ---

def fetch_page_content(url):
    """Busca o conteúdo HTML de uma URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Levanta um erro para códigos HTTP 4xx/5xx
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar {url}: {e}")
        return None


def extract_contact_info(html_content, url):
    """Extrai nome (do título), emails e telefones do conteúdo HTML."""
    if not html_content:
        return {}

    soup = BeautifulSoup(html_content, 'html.parser')
    data = {
        "nome_site": soup.title.string.strip() if soup.title else "N/A",
        "emails": set(),  # Usar set para evitar duplicatas
        "telefones": set(),
        "url": url,
        "endereco_estimado": "Não extraído"  # Placeholder
    }

    # Extrair emails
    found_emails = re.findall(EMAIL_REGEX, html_content)
    for email in found_emails:
        # Filtro simples para evitar emails comuns de domínios de imagem/fontes
        if not any(domain in email for domain in ['w3.org', '.png', '.jpg', '.gif', 'example.com', 'sentry.io']):
             data["emails"].add(email.lower())

    # Extrair telefones
    # O texto do body pode ser mais produtivo para telefones e emails do que o html_content inteiro
    # já que pode evitar scripts e tags style.
    text_content = soup.get_text(separator=" ")
    found_phones = re.findall(PHONE_REGEX, text_content)
    data["telefones"].update(found_phones)

    # Tentar extrair endereço (MUITO básico e propenso a erros)
    # Esta é uma heurística simples e pode precisar de muito refinamento.
    # Procura por texto próximo a palavras-chave como "Endereço:", "Rua", "Av."
    address_keywords = ['endereço', 'rua', 'avenida', 'av.', 'cep']
    possible_addresses = []
    for keyword in address_keywords:
        # Busca por tags que contenham a palavra-chave (case-insensitive)
        tags_with_keyword = soup.find_all(
            string=re.compile(keyword, re.IGNORECASE))
        for tag_content in tags_with_keyword:
            parent_text = tag_content.find_parent().get_text(separator=' ', strip=True)
            # Limita o tamanho do texto para evitar capturas muito grandes e irrelevantes
            if len(parent_text) < 200:  # Ajuste este limite conforme necessário
                possible_addresses.append(parent_text)

    if possible_addresses:
        # Aqui eu posso adicionar uma lógica para escolher o "melhor" endereço
        # ou apenas pegar o primeiro encontrado que pareça razoável.
        # Por simplicidade, vou concatenar os primeiros encontrados (até um limite)
        # e remover duplicatas mantendo a ordem
        unique_addresses = list(dict.fromkeys(possible_addresses))
        # Pega até 2 para não ficar muito longo
        data["endereco_estimado"] = " | ".join(unique_addresses[:2])

    return data

# --- Lógica Principal ---


def main():
    """Função principal para buscar e extrair leads."""
    all_leads = []
    print("Iniciando busca por leads...")

    for query in QUERIES:
        print(f"\nBuscando por: '{query}'")
        try:
            # A biblioteca 'google' pode ter parâmetros diferentes.
            # A 'googlesearch-python' usa search(query, num_results=...)
            # O parâmetro 'lang' ajuda a obter resultados em português do Brasil.
            # 'pause' adiciona um delay entre as buscas ao Google para evitar bloqueios.
            search_results_urls = list(
                search(query, num_results=NUM_RESULTS_PER_QUERY, lang='pt-br'))

            if not search_results_urls:
                print(f"Nenhum resultado encontrado para '{query}'.")
                continue

            for url in search_results_urls:
                print(f"  Processando: {url}")
                html_content = fetch_page_content(url)
                if html_content:
                    contact_info = extract_contact_info(html_content, url)
                    if contact_info.get("emails") or contact_info.get("telefones"):
                        print(
                            f"    -> Lead encontrado: {contact_info.get('nome_site')}")
                        print(
                            f"       Emails: {', '.join(contact_info.get('emails', []))}")
                        print(
                            f"       Telefones: {', '.join(contact_info.get('telefones', []))}")
                        print(
                            f"       Endereço Estimado: {contact_info.get('endereco_estimado', 'N/A')}")
                        all_leads.append(contact_info)
                    else:
                        print(
                            f"    -> Nenhuma informação de contato clara encontrada em {contact_info.get('nome_site')}.")
                # Pausa entre o processamento de cada página
                sleep(REQUEST_DELAY)

        except Exception as e:
            print(f"Ocorreu um erro ao processar a query '{query}': {e}")
            print("Isso pode ser devido a bloqueio do Google. Tente aumentar o 'pause' ou usar menos queries/resultados.")
            sleep(10)  # Pausa maior se houver erro na busca

    print("\n--- Relatório Final de Leads ---")
    if all_leads:
        for lead in all_leads:
            print(f"Nome/Site: {lead['nome_site']}")
            print(f"  URL: {lead['url']}")
            print(
                f"  Emails: {', '.join(lead['emails']) if lead['emails'] else 'Nenhum'}")
            print(
                f"  Telefones: {', '.join(lead['telefones']) if lead['telefones'] else 'Nenhum'}")
            print(f"  Endereço Estimado: {lead['endereco_estimado']}")
            print("-" * 30)
    else:
        print("Nenhum lead com email ou telefone foi encontrado.")

    # Salvar em um arquivo CSV
    if all_leads:
        keys = all_leads[0].keys()
        with open('leads.csv', 'w', newline='', encoding='utf-8-sig') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_leads)
        print("\nLeads salvos em leads.csv")

if __name__ == "__main__":
    main()

# Configuração para Windows
if sys.platform.startswith("win"):
    import os
    os.system('chcp 65001')