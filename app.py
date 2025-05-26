from flask import Flask, render_template, request
from busca_leads import buscar_leads

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        estado = request.form['estado']
        cidade = request.form['cidade']
        tipo = request.form['tipo']
        quantidade = int(request.form['quantidade'])

        # Construir a query
        query = f"{tipo} {cidade} {estado}"
        arquivo_csv = buscar_leads([query], quantidade)

        return f"<p>Busca finalizada! <a href='/static/leads/{arquivo_csv}'>Clique aqui para baixar o arquivo</a></p>"

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
