from flask import Flask, render_template, request, redirect, url_for, session, Response
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import csv
from io import StringIO

app = Flask(__name__)

app.secret_key = 'sua_chave_secreta_aqui'
# MANTIDA A SUA CONEXÃO COM POSTGRESQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin@localhost/appcompravenda'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS ---
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

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
    vendedor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True) # ATRELADO AO VENDEDOR
    quantidade = db.Column(db.Integer, nullable=False)
    
    cliente = db.relationship('Cliente', backref=db.backref('vendas', lazy=True))
    produto = db.relationship('Produto', backref=db.backref('vendas', lazy=True))
    vendedor = db.relationship('Usuario', backref=db.backref('vendas', lazy=True)) # RELAÇÃO COM USUÁRIO

# --- INICIALIZAÇÃO DO BANCO E USUÁRIOS ---
with app.app_context():
    db.create_all()
    
    # Verifica se o admin existe pelo email, se não, cria
    if not Usuario.query.filter_by(email='admin@loja.com').first():
        admin = Usuario(nome='Chefe (Admin)', email='admin@loja.com', senha='123', is_admin=True)
        db.session.add(admin)
        db.session.commit()
        
    # Verifica se o vendedor existe, se não, cria
    if not Usuario.query.filter_by(email='vendedor@loja.com').first():
        vendedor = Usuario(nome='Vendedor Padrão', email='vendedor@loja.com', senha='123', is_admin=False)
        db.session.add(vendedor)
        db.session.commit()

# --- CADEADOS DE SEGURANÇA ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_logado' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Cadeado exclusivo para o Admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return "<h1>Acesso Negado!</h1><p>Apenas o Administrador pode acessar esta página.</p><a href='/vendas'>Voltar para Vendas</a>"
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS DE LOGIN E LOGOUT ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        email_digitado = request.form['email']
        senha_digitada = request.form['password']
        
        user_bd = Usuario.query.filter_by(email=email_digitado, senha=senha_digitada).first()
        
        if user_bd:
            session['usuario_logado'] = user_bd.email
            session['usuario_nome'] = user_bd.nome
            session['is_admin'] = user_bd.is_admin
            
            if user_bd.is_admin:
                return redirect(url_for('index'))
            else:
                return redirect(url_for('vendas'))
        else:
            erro = "E-mail ou senha incorretos!"
            
    return render_template('login.html', erro=erro)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- NOVA ROTA DE USUÁRIOS ---
@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
@admin_required
def usuarios():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        is_admin = True if request.form.get('is_admin') == 'on' else False
        
        novo_usuario = Usuario(nome=nome, email=email, senha=senha, is_admin=is_admin)
        db.session.add(novo_usuario)
        db.session.commit()
        return redirect('/usuarios')
        
    lista_usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=lista_usuarios)

# --- ROTA DO DASHBOARD (SÓ ADMIN) ---
@app.route('/')
@login_required
@admin_required
def index():
    total_produtos = Produto.query.count()
    total_clientes = Cliente.query.count()
    total_vendas = Venda.query.count()
    todas_vendas = Venda.query.all()
    receita_total = sum(v.quantidade * v.produto.preco for v in todas_vendas)
    
    limite_minimo = 5 
    produtos_baixo_estoque = Produto.query.filter(Produto.estoque <= limite_minimo).all()
    
    todos_produtos = Produto.query.all()
    nomes_produtos = [p.nome for p in todos_produtos]
    estoques_produtos = [p.estoque for p in todos_produtos]
    
    return render_template('index.html', 
                           total_produtos=total_produtos, 
                           total_clientes=total_clientes, 
                           total_vendas=total_vendas, 
                           receita_total=receita_total,
                           produtos_baixo_estoque=produtos_baixo_estoque,
                           nomes_produtos=nomes_produtos,
                           estoques_produtos=estoques_produtos)

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
@admin_required
def excluir_produto(id):
    produto = Produto.query.get(id)
    if produto:
        vendas = Venda.query.filter_by(produto_id=id).all()
        for venda in vendas:
            db.session.delete(venda)
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
@admin_required
def excluir_cliente(id):
    cliente = Cliente.query.get(id)
    if cliente:
        vendas = Venda.query.filter_by(cliente_id=id).all()
        for venda in vendas:
            db.session.delete(venda)
        db.session.delete(cliente)
        db.session.commit()
    return redirect('/clientes')

# --- ROTAS DE VENDAS ---
@app.route('/vendas', methods=['GET', 'POST'])
@login_required
def vendas():
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        produto_id = request.form['produto_id']
        quantidade = int(request.form['quantidade'])
        produto = Produto.query.get(produto_id)
        
        # BUSCA O VENDEDOR LOGADO
        email_logado = session['usuario_logado']
        vendedor_atual = Usuario.query.filter_by(email=email_logado).first()
        
        if produto.estoque >= quantidade:
            produto.estoque -= quantidade
            # SALVA O ID DO VENDEDOR NA VENDA
            nova_venda = Venda(cliente_id=cliente_id, produto_id=produto_id, quantidade=quantidade, vendedor_id=vendedor_atual.id)
            db.session.add(nova_venda)
            db.session.commit()
            return redirect('/vendas')
        else:
            return f"<h1>Erro: Estoque insuficiente! O produto {produto.nome} só tem {produto.estoque} unidades.</h1><br><a href='/vendas'>Voltar</a>"
    
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
@admin_required
def excluir_venda(id):
    venda = Venda.query.get(id)
    if venda:
        venda.produto.estoque += venda.quantidade
        db.session.delete(venda)
        db.session.commit()
    return redirect('/vendas')

@app.route('/exportar_relatorio')
@login_required
@admin_required
def exportar_relatorio():
    todas_vendas = Venda.query.all()
    
    si = StringIO()
    cw = csv.writer(si, delimiter=';') 
    
    # ADICIONADA A COLUNA DE VENDEDOR NO EXCEL
    cw.writerow(['ID da Venda', 'Vendedor', 'Cliente', 'Produto', 'Quantidade', 'Preço Unitário', 'Total da Venda'])
    
    for v in todas_vendas:
        total = v.quantidade * v.produto.preco
        nome_vendedor = v.vendedor.nome if v.vendedor else "Vendedor Apagado"
        
        cw.writerow([
            v.id, 
            nome_vendedor,
            v.cliente.nome, 
            v.produto.nome, 
            v.quantidade, 
            f"R$ {v.produto.preco:.2f}".replace('.', ','), 
            f"R$ {total:.2f}".replace('.', ',')
        ])
        
    output = Response(si.getvalue().encode('utf-8-sig'), mimetype='text/csv')
    output.headers["Content-Disposition"] = "attachment; filename=relatorio_vendas.csv"
    
    return output

# --- NOVA ROTA: GERAR RECIBO ---
@app.route('/recibo/<int:id>')
@login_required
def recibo(id):
    # Busca a venda específica pelo ID
    venda = Venda.query.get_or_404(id)
    return render_template('recibo.html', venda=venda)

if __name__ == '__main__':
    app.run(debug=True)