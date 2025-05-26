import requests
from bs4 import BeautifulSoup
import re
from time import sleep
from googlesearch import search
import csv
import sys
from datetime import datetime
import os

# --- Configurações Iniciais ---
# Lista de palavras-chave para busca!
QUERIES = [
    "escola tecnica campinas",
]

# Número de resultados do Google para processar por query
NUM_RESULTS_PER_QUERY = 100

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

# --- Funções Auxiliares Aprimoradas ---


def generate_filename(base_name):
    """Gera um nome de arquivo único com timestamp"""
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{now}.csv"


def save_leads_to_csv(leads, filename_prefix='leads_coletados'):
    """Salva os leads em CSV com estrutura organizada, otimizado para Excel."""

    if not leads:
        print("Nenhum lead para salvar.")
        return

    filename = generate_filename(filename_prefix)

    # Preparar dados para CSV com colunas estruturadas
    csv_rows = []
    max_emails_found = 0
    max_phones_found = 0

    # Primeiro, iterar para determinar o número máximo de emails/telefones
    # e para preparar as linhas básicas.
    for lead in leads:
        if lead.get('emails'):
            max_emails_found = max(
                max_emails_found, len(lead.get('emails', set())))
        if lead.get('telefones'):
            max_phones_found = max(max_phones_found, len(
                lead.get('telefones', set())))

    # Agora, construir as linhas, garantindo colunas para todos os emails/telefones
    for lead in leads:
        row = {
            'Nome do Site/Empresa': lead.get('nome_site', 'N/A'),
            'URL': lead.get('url', ''),
            'Endereço Estimado': lead.get('endereco_estimado', 'Não extraído'),
            'Data Coleta': datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Data da gravação do CSV
        }

        # Adicionar emails em colunas separadas (Email 1, Email 2, etc.)
        emails = list(lead.get('emails', set()))
        for i in range(max_emails_found):
            row[f'Email {i+1}'] = emails[i] if i < len(emails) else ''

        # Adicionar telefones em colunas separadas (Telefone 1, Telefone 2, etc.)
        phones = list(lead.get('telefones', set()))
        for i in range(max_phones_found):
            row[f'Telefone {i+1}'] = phones[i] if i < len(phones) else ''

        csv_rows.append(row)

    # Determinar todas as colunas possíveis de forma ordenada
    base_columns = ['Nome do Site/Empresa',
                    'URL', 'Endereço Estimado', 'Data Coleta']
    email_columns = [f'Email {i+1}' for i in range(max_emails_found)]
    phone_columns = [f'Telefone {i+1}' for i in range(max_phones_found)]

    fieldnames = base_columns + email_columns + phone_columns

    # Escrever arquivo CSV
    try:
        # Usar delimiter=';' para melhor compatibilidade com Excel em algumas regiões
        # Usar encoding='utf-8-sig' para que o Excel entenda acentos corretamente
        with open(filename, 'w', newline='', encoding='utf-8-sig', errors='replace') as csvfile:
            writer = csv.DictWriter(
                csvfile, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()  # Escreve o cabeçalho (nomes das colunas)
            writer.writerows(csv_rows)  # Escreve todas as linhas de dados
        print(f"\nLeads salvos com sucesso em: {filename}")
        print(f"O arquivo foi salvo com ';' como delimitador e codificação UTF-8 com BOM para melhor compatibilidade com Excel.")
    except IOError as e:
        print(f"Erro de E/S ao salvar o arquivo CSV: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao salvar o CSV: {e}")

# --- Lógica Principal ---

def main():
    """Função principal para buscar e extrair leads."""
    all_leads = []
    print("Iniciando busca por leads...")

    for query in QUERIES:
        print(f"\nBuscando por: '{query}'")
        try:
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
                sleep(REQUEST_DELAY)

        except Exception as e:
            print(f"Ocorreu um erro ao processar a query '{query}': {e}")
            sleep(10)

    print("\n--- Relatório Final de Leads ---")
    if all_leads:
        for lead in all_leads:
            print(f"\nNome/Site: {lead['nome_site']}")
            print(f"URL: {lead['url']}")
            print(
                f"Emails: {', '.join(lead['emails']) if lead['emails'] else 'Nenhum'}")
            print(
                f"Telefones: {', '.join(lead['telefones']) if lead['telefones'] else 'Nenhum'}")
            print(f"Endereço Estimado: {lead['endereco_estimado']}")
        print("\n" + "="*50)

        # Salvar os leads em CSV
        save_leads_to_csv(all_leads)
    else:
        print("Nenhum lead com email ou telefone foi encontrado.")


if __name__ == "__main__":
    main()

    # Configuração para Windows
    if sys.platform.startswith("win"):
        import os
        os.system('chcp 65001')
