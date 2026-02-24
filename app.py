from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

app = Flask(__name__)

# Configuração de Segurança (Necessário para usar Login/Sessão)
app.secret_key = 'sua_chave_secreta_aqui'

# Configuração do Banco de Dados PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin@localhost/appcompravenda'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS (TABELAS DO BANCO) ---
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    estoque = db.Column(db.Integer, nullable=False, default=0)

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

# Cria as tabelas e o usuário padrão
with app.app_context():
    db.create_all()
    # Cria o usuário admin se não existir nenhum
    if not Usuario.query.first():
        admin = Usuario(username='admin', password='123')
        db.session.add(admin)
        db.session.commit()

# --- CADEADO DE SEGURANÇA (DECORATOR) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_logado' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS DE LOGIN E LOGOUT ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        usuario = request.form['username']
        senha = request.form['password']
        
        user_bd = Usuario.query.filter_by(username=usuario, password=senha).first()
        
        if user_bd:
            session['usuario_logado'] = user_bd.username
            return redirect(url_for('index'))
        else:
            erro = "Usuário ou senha incorretos!"
            
    return render_template('login.html', erro=erro)

@app.route('/logout')
def logout():
    session.pop('usuario_logado', None)
    return redirect(url_for('login'))

# --- ROTA DO DASHBOARD ---
@app.route('/')
@login_required
def index():
    total_produtos = Produto.query.count()
    total_clientes = Cliente.query.count()
    total_vendas = Venda.query.count()
    todas_vendas = Venda.query.all()
    receita_total = sum(v.quantidade * v.produto.preco for v in todas_vendas)
    return render_template('index.html', total_produtos=total_produtos, total_clientes=total_clientes, total_vendas=total_vendas, receita_total=receita_total)

# --- ROTAS DE PRODUTOS ---
@app.route('/produtos', methods=['GET', 'POST'])
@login_required
def produtos():
    if request.method == 'POST':
        nome = request.form['nome']
        preco = request.form['preco']
        estoque = request.form['estoque']
        novo_produto = Produto(nome=nome, preco=float(preco), estoque=int(estoque))
        db.session.add(novo_produto)
        db.session.commit()
        return redirect('/produtos')
    lista_produtos = Produto.query.all()
    return render_template('produtos.html', produtos=lista_produtos)

@app.route('/editar_produto/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_produto(id):
    produto = Produto.query.get_or_404(id)
    if request.method == 'POST':
        produto.nome = request.form['nome']
        produto.preco = float(request.form['preco'])
        produto.estoque = int(request.form['estoque'])
        db.session.commit()
        return redirect('/produtos')
    return render_template('editar_produto.html', produto=produto)

@app.route('/excluir_produto/<int:id>')
@login_required
def excluir_produto(id):
    produto = Produto.query.get(id)
    if produto:
        db.session.delete(produto)
        db.session.commit()
    return redirect('/produtos')

# --- ROTAS DE CLIENTES ---
@app.route('/clientes', methods=['GET', 'POST'])
@login_required
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

@app.route('/editar_cliente/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    if request.method == 'POST':
        cliente.nome = request.form['nome']
        cliente.email = request.form['email']
        cliente.telefone = request.form['telefone']
        db.session.commit()
        return redirect('/clientes')
    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/excluir_cliente/<int:id>')
@login_required
def excluir_cliente(id):
    cliente = Cliente.query.get(id)
    if cliente:
        db.session.delete(cliente)
        db.session.commit()
    return redirect('/clientes')

# --- ROTAS DE VENDAS (COM ESTOQUE E FILTROS) ---
@app.route('/vendas', methods=['GET', 'POST'])
@login_required
def vendas():
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        produto_id = request.form['produto_id']
        quantidade = int(request.form['quantidade'])
        produto = Produto.query.get(produto_id)
        
        # Verifica se tem estoque
        if produto.estoque >= quantidade:
            produto.estoque -= quantidade
            nova_venda = Venda(cliente_id=cliente_id, produto_id=produto_id, quantidade=quantidade)
            db.session.add(nova_venda)
            db.session.commit()
            return redirect('/vendas')
        else:
            return f"<h1>Erro: Estoque insuficiente! O produto {produto.nome} só tem {produto.estoque} unidades.</h1><br><a href='/vendas'>Voltar</a>"
    
    # Lógica de Filtros (Busca)
    cliente_filtro = request.args.get('cliente_id')
    produto_filtro = request.args.get('produto_id')
    
    query = Venda.query
    
    if cliente_filtro:
        query = query.filter_by(cliente_id=cliente_filtro)
    if produto_filtro:
        query = query.filter_by(produto_id=produto_filtro)
        
    lista_vendas = query.all()
    lista_clientes = Cliente.query.all()
    lista_produtos = Produto.query.all()
    
    return render_template('vendas.html', 
                           vendas=lista_vendas, 
                           clientes=lista_clientes, 
                           produtos=lista_produtos,
                           cliente_filtro=cliente_filtro,
                           produto_filtro=produto_filtro)

@app.route('/excluir_venda/<int:id>')
@login_required
def excluir_venda(id):
    venda = Venda.query.get(id)
    if venda:
        # Devolve para o estoque
        venda.produto.estoque += venda.quantidade
        db.session.delete(venda)
        db.session.commit()
    return redirect('/vendas')

if __name__ == '__main__':
    app.run(debug=True)