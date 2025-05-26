import requests
import csv
from datetime import datetime

ACCESS_TOKEN = 'SEU_TOKEN_AQUI'
PAGE_ID = 'ID_DA_PAGINA'
POST_ID = 'ID_DA_POSTAGEM'


def get_comments(post_id):
    url = f"https://graph.facebook.com/v19.0/{post_id}/comments"
    params = {
        'access_token': ACCESS_TOKEN,
        'fields': 'from,message,created_time',
        'limit': 100
    }
    response = requests.get(url, params=params)
    return response.json().get('data', [])


def save_filtered_comments(comments, keywords, filename='leads_facebook'):
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{filename}_{now}.csv"
    leads = []

    for comment in comments:
        message = comment.get('message', '').lower()
        if any(keyword in message for keyword in keywords):
            user = comment.get('from', {})
            profile_url = f"https://facebook.com/{user.get('id')}"
            leads.append({
                'Nome': user.get('name', 'Desconhecido'),
                'Mensagem': comment['message'],
                'Data': comment.get('created_time'),
                'Perfil': profile_url
            })

    if leads:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(
                csvfile, fieldnames=leads[0].keys(), delimiter=';')
            writer.writeheader()
            writer.writerows(leads)
        print(f"Arquivo salvo: {filename}")
    else:
        print("Nenhum comentário relevante encontrado.")


# Exemplo de uso
keywords = ['quero pós', 'quero fazer pós', 'quero uma pós graduação']
comentarios = get_comments(POST_ID)
save_filtered_comments(comentarios, keywords)
