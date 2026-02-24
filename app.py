from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuração do Banco de Dados PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin@localhost/appcompravenda'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o banco de dados
db = SQLAlchemy(app)

# --- MODELOS (TABELAS DO BANCO) ---
class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)

class Venda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    
    cliente = db.relationship('Cliente', backref=db.backref('vendas', lazy=True))
    produto = db.relationship('Produto', backref=db.backref('vendas', lazy=True))

# Cria as tabelas automaticamente no Postgres
with app.app_context():
    db.create_all()

# --- ROTA DO DASHBOARD (PÁGINA INICIAL) ---
@app.route('/')
def index():
    # Faz as contagens no banco de dados
    total_produtos = Produto.query.count()
    total_clientes = Cliente.query.count()
    total_vendas = Venda.query.count()
    
    # Calcula a receita total de todas as vendas
    todas_vendas = Venda.query.all()
    receita_total = sum(v.quantidade * v.produto.preco for v in todas_vendas)
    
    return render_template('index.html', 
                           total_produtos=total_produtos, 
                           total_clientes=total_clientes, 
                           total_vendas=total_vendas, 
                           receita_total=receita_total)

# --- ROTAS DE PRODUTOS ---
@app.route('/produtos', methods=['GET', 'POST'])
def produtos():
    if request.method == 'POST':
        nome = request.form['nome']
        preco = request.form['preco']
        novo_produto = Produto(nome=nome, preco=float(preco))
        db.session.add(novo_produto)
        db.session.commit()
        return redirect('/produtos')
    
    lista_produtos = Produto.query.all()
    return render_template('produtos.html', produtos=lista_produtos)

@app.route('/excluir_produto/<int:id>')
def excluir_produto(id):
    produto = Produto.query.get(id)
    if produto:
        db.session.delete(produto)
        db.session.commit()
    return redirect('/produtos')

# --- ROTAS DE CLIENTES ---
@app.route('/clientes', methods=['GET', 'POST'])
def clientes():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        novo_cliente = Cliente(nome=nome, email=email, telefone=telefone)
        db.session.add(novo_cliente)
        db.session.commit()
        return redirect('/clientes')
    
    lista_clientes = Cliente.query.all()
    return render_template('clientes.html', clientes=lista_clientes)

@app.route('/excluir_cliente/<int:id>')
def excluir_cliente(id):
    cliente = Cliente.query.get(id)
    if cliente:
        db.session.delete(cliente)
        db.session.commit()
    return redirect('/clientes')

# --- ROTAS DE VENDAS ---
@app.route('/vendas', methods=['GET', 'POST'])
def vendas():
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        produto_id = request.form['produto_id']
        quantidade = request.form['quantidade']
        
        nova_venda = Venda(cliente_id=cliente_id, produto_id=produto_id, quantidade=int(quantidade))
        db.session.add(nova_venda)
        db.session.commit()
        return redirect('/vendas')
    
    lista_vendas = Venda.query.all()
    lista_clientes = Cliente.query.all()
    lista_produtos = Produto.query.all()
    
    return render_template('vendas.html', vendas=lista_vendas, clientes=lista_clientes, produtos=lista_produtos)

@app.route('/excluir_venda/<int:id>')
def excluir_venda(id):
    venda = Venda.query.get(id)
    if venda:
        db.session.delete(venda)
        db.session.commit()
    return redirect('/vendas')

if __name__ == '__main__':
    app.run(debug=True)