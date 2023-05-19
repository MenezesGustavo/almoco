from flask import Flask, jsonify, flash, render_template, request, redirect, url_for, session, Response
from sqlalchemy import func, create_engine, text
from datetime import date, timedelta
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import datetime
import psycopg2
now = datetime.datetime.now()
today = date.today()

pedido = Flask(__name__)


pedido.secret_key = 'my_secret_key'  # Set a secret key for session security
conn_string = 'postgresql://postgres:root@localhost/postgres'

pedido.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:root@localhost/postgres'
db2 = SQLAlchemy(pedido)


class Cart(db2.Model):
    __tablename__ = 'carrinho'  # Nome da tabela no banco de dados

    id = db2.Column(db2.Integer, primary_key=True)
    username = db2.Column(db2.String(50))
    equipe = db2.Column(db2.String(50))
    horaentrega = db2.Column(db2.String(50))
    horapedido = db2.Column(db2.String(50))
    restaurante = db2.Column(db2.String(50))
    prato = db2.Column(db2.String(50))
    informacao = db2.Column(db2.String(50))

    def __repr__(self):
        return f"<Cart(id={self.id})>"
    

class Food(db2.Model):
    pedidonumero = db2.Column(db2.Integer, primary_key=True)
    entregarestaurante = db2.Column(db2.DateTime)



db = create_engine(conn_string)

conn = db.connect()

cart_count = ""


users = {
    'gerente': 'senha1',
    'boali': 'senha2',
    'villa': 'senha3'
}


@pedido.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('order_dish'))
    else:
        return render_template('login.html')


@pedido.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST':
        user = request.form['user']
        password = request.form['password']

        if user in users and users[user] == password:
            session['user'] = user
            if user == 'gerente':
                return redirect('/cart')
            else:
                return redirect('/ordersrest')
        else:
            error_message = 'Usuário ou senha inválidos'
            return render_template('login.html', error_message=error_message)

    return render_template('login.html')


@pedido.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# Envio unico almoco-----------------------------------------------------------


@pedido.route("/almoco", methods=["GET", "POST"])
def almoco():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    return redirect(url_for('cart_insert'))


# Envio para o carrinho-------------------------------------------------------------


@pedido.route('/cart', methods=['POST', 'GET'])
def cart_insert():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    user = session['user']

    from datetime import datetime, timedelta

    if request.method == 'POST':
        data = request.get_json()
        cart = Cart(
            username=data['username'],
            equipe=data['equipe'],
            horaentrega=data['horaentrega'],
            horapedido=data['horapedido'],
            restaurante=data['restaurante'],
            prato=data['prato'],
            informacao=data['informacao']
        )
        db2.session.add(cart)
        db2.session.commit()
        return 'Pedido incluído com sucesso!'
    
    query = db2.session.query(func.count(Cart.id))
    cart_count = query.scalar()
    if cart_count > 0:
        print(f"Valor da contagem: {cart_count}")

    times = [(datetime.strptime("11:00", "%H:%M") +
              timedelta(minutes=15 * i)).strftime("%H:%M") for i in range(25)]
    return render_template("cart.html", times=times, cart_count=cart_count, user=user)



@pedido.route("/orderdone")
def order_done():
    orderfeita = pd.read_sql("select * from \"food\"", db)

    pedidoorder = orderfeita.tail(1)
    pedidonumero = pedidoorder['pedidonumero'].iloc[0]

    print(pedidonumero)
    return render_template("orderdone.html", pedidonumero=pedidonumero)

# --------------------------------------------------------------------


@pedido.route("/ordercart")
def order_cart():
    orderfeita = pd.read_sql("select * from \"carrinho\"", db)
    pedidoorder = orderfeita.tail(1)
    pedidonumero = pedidoorder['pedidonumero'].iloc[0]

    print(pedidonumero)
    return render_template("ordercart.html", pedidonumero=pedidonumero)


# --------------------------------------------------------------------


@pedido.route("/checkorders", methods=["GET", "POST"])
def check_orders():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    user = session['user']

    orders = pd.DataFrame()
    orders_exist = False

    from datetime import datetime, timedelta

    if request.method == "POST":
        date = request.form["date"]
        query = f"SELECT * FROM food WHERE dia = '{date}'"
        orders = pd.read_sql(query, con=db)
        if not orders.empty:
            orders_exist = True
            orders = orders.to_dict('records')

    cart_nr = db2.session.query(func.count(Cart.id))
    cart_count = cart_nr.scalar()
    if cart_count > 0:
        print(f"Valor da contagem: {cart_count}")
            
    foods = Food.query.filter(Food.entregarestaurante == '').order_by(Food.pedidonumero.asc()).all()

    times = [(datetime.strptime("11:00", "%H:%M") +
              timedelta(minutes=15 * i)).strftime("%H:%M") for i in range(25)]

    return render_template("checkorders.html", times=times, orders=orders, orders_exist=orders_exist,cart_count=cart_count, user=user, foods=foods)



@pedido.route("/ordersrest", methods=["GET", "POST"])
def orders_rest():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']
    orders = pd.DataFrame()
    orders_exist = False
    if user == 'boali':
        if request.method == "POST":
            selected_date = request.form["date"]
            query = f"SELECT * FROM food WHERE dia = '{selected_date}' AND restaurante = 'Boali'"
            orders = pd.read_sql(query, con=db)
            if not orders.empty:
                orders_exist = True
                orders = orders.to_dict('records')
                foods = Food.query.filter(Food.entregarestaurante == '').order_by(Food.pedidonumero.asc()).all()
        else:
            today = date.today()
            query = f"SELECT * FROM food WHERE dia = '{today}' AND restaurante = 'Boali'"
            orders = pd.read_sql(query, con=db)
            if not orders.empty:
                orders_exist = True
                orders = orders.to_dict('records')
                foods = Food.query.filter(Food.entregarestaurante == '').order_by(Food.pedidonumero.asc()).all()
    elif user == 'villa':
        if request.method == "POST":
            selected_date = request.form["date"]
            query = f"SELECT * FROM food WHERE dia = '{selected_date}' AND restaurante = 'Villa'"
            orders = pd.read_sql(query, con=db)
            if not orders.empty:
                orders_exist = True
                orders = orders.to_dict('records')
                foods = Food.query.filter(Food.entregarestaurante == '').order_by(Food.pedidonumero.asc()).all()
        else:
            today = date.today()
            query = f"SELECT * FROM food WHERE dia = '{today}' AND restaurante = 'Villa'"
            orders = pd.read_sql(query, con=db)
            if not orders.empty:
                orders_exist = True
                orders = orders.to_dict('records')
                foods = Food.query.filter(Food.entregarestaurante == '').order_by(Food.pedidonumero.asc()).all()
    else:
        if request.method == "POST":
            selected_date = request.form["date"]
            query = f"SELECT * FROM food WHERE dia = '{selected_date}'"
            orders = pd.read_sql(query, con=db)
            if not orders.empty:
                orders_exist = True
                orders = orders.to_dict('records')
                foods = Food.query.filter(Food.entregarestaurante == '').order_by(Food.pedidonumero.asc()).all()
        else:
            today = date.today()
            query = f"SELECT * FROM food WHERE dia = '{today}'"
            orders = pd.read_sql(query, con=db)
            if not orders.empty:
                orders_exist = True
                orders = orders.to_dict('records')
                foods = Food.query.filter(Food.entregarestaurante == '').order_by(Food.pedidonumero.asc()).all()
    

    
    foods = Food.query.filter(Food.entregarestaurante == '').order_by(Food.pedidonumero.asc()).all()

    return render_template("ordersrest.html", orders=orders, orders_exist=orders_exist, user=user, foods=foods)

# --------------------------------------------------------------------


@pedido.route("/cartlist", methods=["GET", "POST"])
def cartlist():

    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']

    orders = pd.DataFrame()
    orders_exist = False

    query = f"SELECT * FROM carrinho"
    orders = pd.read_sql(query, con=db)
    if not orders.empty:
        orders_exist = True
        orders = orders.to_dict('records')

    
    cart_nr = db2.session.query(func.count(Cart.id))
    cart_count = cart_nr.scalar()
    if cart_count > 0:
        print(f"Valor da contagem: {cart_count}")
    

    return render_template("cartlist.html", orders=orders, orders_exist=orders_exist, cart_count=cart_count, user=user)


# Enviar carrinho--------------------------------------------------------------------
@pedido.route("/cartfood", methods=["GET", "POST"])
def cartfood():
    conn = db.connect()
    cart_items = pd.read_sql("SELECT * FROM \"carrinho\"", conn)

    for _, row in cart_items.iterrows():
        username = row["username"]
        equipe = row["equipe"]
        horaentrega = row["horaentrega"]
        horapedido = row["horapedido"]
        restaurante = row["restaurante"]
        prato = row["prato"]
        dia = date.today()
        informacao = row["informacao"]

        moveQuery = text("INSERT INTO \"food\" (username, equipe, horaentrega, horapedido, restaurante, prato, dia,informacao) VALUES (:username, :equipe, :horaentrega, :horapedido, :restaurante, :prato, :dia, :informacao)")
        parameters = {
            "username": username,
            "equipe": equipe,
            "horaentrega": horaentrega,
            "horapedido": horapedido,
            "restaurante": restaurante,
            "prato": prato,
            "dia": dia,
            "informacao" : informacao
        }

        deleteQuery = text("DELETE FROM carrinho")

        conn.execute(moveQuery, parameters)
        conn.execute(deleteQuery)

    conn.commit()
    conn.close()

    return redirect(url_for('cart_insert'))



# Deletar Item Carrinho-------------------------------------------------------------


@pedido.route('/deleteitem', methods=['POST'])
def delete_item():
    orderId = request.json['id']
    item = db2.session.get(Cart, orderId)

    if item:
        db2.session.delete(item)
        db2.session.commit()
        return redirect(url_for('cartlist'))

# Atualizar entrega -------------------------------------------------------------

@pedido.route('/updatefooddelivery', methods=['POST'])
def update_food_delivery():
    pedidonumero = request.json['pedidonumero']
    entregueas = request.json['entregueas']

    food = Food.query.filter_by(pedidonumero=pedidonumero).first()

    print(entregueas)

    if food:
        food.entregarestaurante = entregueas
        db2.session.commit()
        return jsonify({'success': True})
    
    return redirect(url_for('checkorders'))



if __name__ == '__main__':
    pedido.run(debug=True, use_reloader=False, port=5001)
