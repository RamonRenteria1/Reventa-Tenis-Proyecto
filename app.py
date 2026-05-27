from flask import Flask, render_template, request, redirect, url_for, session, flash
from tiendatenis import TiendaTenis
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)
app.secret_key = "1029300192"

tienda = TiendaTenis()

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "shoesstorenr@gmail.com"
app.config["MAIL_PASSWORD"] = "jzmedprekphjkeyr"

mail = Mail(app)


serializer = URLSafeTimedSerializer(app.secret_key)

@app.route("/", methods=["GET", "POST"])
def login():

    if "usuario_id" in session:
        return redirect(url_for("tienda_T"))

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        usuario = tienda.iniciar_sesion(
            email,
            password
        )

        if not usuario:
            flash("Correo o contraseña incorrectos", "danger")
            return redirect(url_for("login"))

        session["usuario_id"] = str(usuario["_id"])
        session["nombre"] = usuario["nombre"]
        session["tipo"] = usuario["tipo"]

        flash("Bienvenido", "success")
        return redirect(url_for("tienda_T"))

    return render_template("login.html")

@app.route("/registro", methods=["GET", "POST"])
def registro():

    if request.method == "POST":

        nombre = request.form["nombre"]
        email = request.form["email"]

        password_original = request.form["password"]
        confirmar_password = request.form["confirmar_password"]

        if password_original != confirmar_password:
            flash("Las contraseñas no coinciden", "danger")
            return redirect(url_for("registro"))

        tipo = request.form["tipo"]

        usuario_id = tienda.crear_usuario(
            nombre,
            email,
            password_original,  
            tipo
        )

        if not usuario_id:
            flash("El usuario ya existe", "danger")
            return redirect(url_for("registro"))

        flash("Usuario registrado correctamente","success")
        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/tienda")
def tienda_T():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    marcas = request.args.getlist("marca")
    condiciones = request.args.getlist("condicion")
    colores = request.args.getlist("color")
    busqueda = request.args.get("buscar", "").strip()
    precio_min = request.args.get("precio_min", "").strip()
    precio_max = request.args.get("precio_max", "").strip()

    filtros = {"activo": True}

    if marcas:
        filtros["marca"] = {"$in": marcas}

    if condiciones:
        filtros["condicion"] = {"$in": condiciones}

    if colores:
        filtros["color"] = {"$in": colores}

    if precio_min or precio_max:
        filtros["precio"] = {}
        if precio_min:
            try:
                filtros["precio"]["$gte"] = float(precio_min)
            except:
                pass
        if precio_max:
            try:
                filtros["precio"]["$lte"] = float(precio_max)
            except:
                pass

    if busqueda:
        patrón = {"$regex": busqueda, "$options": "i"}
        filtros["$or"] = [
            {"nombre": patrón},
            {"marca": patrón},
            {"modelo": patrón},
            {"tipo": patrón},
            {"color": patrón}
        ]

    productos = tienda.obtener_productos(filtros)

    return render_template(
        "tienda.html",
        productos=productos
    )
    
@app.route("/eliminar_producto/<producto_id>", methods=["POST"])
def eliminar_producto(producto_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    producto = tienda.productos.find_one({
        "_id": ObjectId(producto_id),
        "activo": True
    })

    if not producto:
        flash("El producto no existe", "danger")
        return redirect(url_for("tienda_T"))

    if str(producto["id_vendedor"]) != session["usuario_id"]:
        flash("No puedes eliminar una publicación que no es tuya", "danger")
        return redirect(url_for("tienda_T"))

    tienda.productos.update_one(
        {"_id": ObjectId(producto_id)},
        {
            "$set": {
                "activo": False,
                "fecha_eliminacion": datetime.now()
            }
        }
    )

    flash("Publicación eliminada correctamente", "success")
    return redirect(url_for("tienda_T"))


@app.route("/perfil")
def perfil():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario = tienda.obtener_usuario(session["usuario_id"])

    if not usuario:
        return redirect(url_for("login"))

    return render_template(
        "perfil.html",
        usuario=usuario
    )


@app.route("/editar_perfil", methods=["GET", "POST"])
def editar_perfil():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario = tienda.obtener_usuario(session["usuario_id"])

    if not usuario:
        return redirect(url_for("login"))

    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        email = request.form["email"].strip().lower()

        if not nombre or not email:
            flash("Nombre y correo son obligatorios", "warning")
            return redirect(url_for("editar_perfil"))

        existente = tienda.usuarios.find_one({
            "email": email,
            "_id": {"$ne": ObjectId(session["usuario_id"])}
        })

        if existente:
            flash("El correo ya está en uso", "danger")
            return redirect(url_for("editar_perfil"))

        tienda.usuarios.update_one(
            {"_id": ObjectId(session["usuario_id"])},
            {"$set": {"nombre": nombre, "email": email}}
        )

        session["nombre"] = nombre
        flash("Perfil actualizado correctamente", "success")
        return redirect(url_for("perfil"))

    return render_template(
        "editar_perfil.html",
        usuario=usuario
    )


@app.route("/acerca")
def acerca():

    return render_template("acerca.html")


@app.route("/agregar_producto", methods=["GET", "POST"])
def agregar_producto():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session["tipo"] != "vendedor":
        return redirect(url_for("tienda_T"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        marca = request.form.get("marca", "").strip()
        tipo = request.form.get("tipo", "").strip()
        color = request.form.get("color", "").strip()
        talla_raw = request.form.get("talla", "").strip()
        stock_raw = request.form.get("stock", "").strip()
        precio_raw = request.form.get("precio", "").strip()
        condicion = request.form.get("condicion", "").strip()
        imagen = request.form.get("imagen", "").strip()

        if not all([nombre, marca, tipo, color, talla_raw, stock_raw, precio_raw, condicion, imagen]):
            return redirect(url_for("agregar_producto"))

        try:
            talla = int(talla_raw)
            stock = int(stock_raw)
            precio = float(precio_raw)
        except ValueError:
            return redirect(url_for("agregar_producto"))

        producto_id = tienda.agregar_producto(
            nombre,
            marca,
            tipo,
            color,
            talla,
            precio,
            condicion,
            stock,
            session["usuario_id"],
            imagen
        )

        if producto_id:
            return redirect(url_for("tienda_T"))

        return redirect(url_for("agregar_producto"))

    return render_template("agregar_producto.html")

@app.route("/editar_producto/<producto_id>", methods=["GET", "POST"])
def editar_producto(producto_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    producto = tienda.productos.find_one({
        "_id": ObjectId(producto_id),
        "activo": True
    })

    if not producto:
        flash("El producto no existe", "danger")
        return redirect(url_for("tienda_T"))

    if str(producto["id_vendedor"]) != session["usuario_id"]:
        flash("No puedes editar una publicación que no es tuya", "danger")
        return redirect(url_for("tienda_T"))

    if request.method == "POST":

        nombre = request.form["nombre"]
        marca = request.form["marca"]
        modelo = request.form["modelo"]
        tipo = request.form["tipo"]
        color = request.form["color"]
        talla = int(request.form["talla"])
        precio = float(request.form["precio"])
        condicion = request.form["condicion"]
        stock = int(request.form["stock"])
        imagen = request.form["imagen"]

        tienda.productos.update_one(
            {"_id": ObjectId(producto_id)},
            {
                "$set": {
                    "nombre": nombre,
                    "marca": marca,
                    "modelo": modelo,
                    "tipo": tipo,
                    "color": color,
                    "talla": talla,
                    "precio": precio,
                    "condicion": condicion,
                    "stock": stock,
                    "imagen": imagen,
                    "fecha_actualizacion": datetime.now()
                }
            }
        )

        flash("Publicación actualizada correctamente", "success")
        return redirect(url_for("tienda_T"))

    producto["_id"] = str(producto["_id"])
    producto["id_vendedor"] = str(producto["id_vendedor"])

    return render_template("editar_producto.html", producto=producto)

@app.route("/recuperar", methods=["GET", "POST"])
def recuperar():

    if request.method == "POST":

        email = request.form["email"]

        usuario = tienda.usuarios.find_one({
            "email": email
        })

        if not usuario:
            flash("No existe una cuenta con ese correo", "danger")
            return redirect(url_for("recuperar"))

        token = serializer.dumps(email, salt="recuperar-password")

        link = url_for(
            "restablecer",
            token=token,
            _external=True
        )

        mensaje = Message(
            "Recuperar contraseña",
            sender=app.config["MAIL_USERNAME"],
            recipients=[email]
        )

        mensaje.body = f"""
        Hola {usuario["nombre"]}

        Para cambiar tu contraseña entra al siguiente link:

        {link}

        Este enlace expira en 15 minutos.
        """

        mail.send(mensaje)

        flash("Te mandamos un correo para cambiar tu contraseña", "success")
        return redirect(url_for("login"))

    return render_template("recuperar.html")

@app.route("/restablecer/<token>", methods=["GET", "POST"])
def restablecer(token):

    try:
        email = serializer.loads(
            token,
            salt="recuperar-password",
            max_age=900
        )

    except:
        flash("El enlace no es válido o ya expiró", "danger")
        return redirect(url_for("recuperar"))

    if request.method == "POST":

        nueva_password = request.form["password"]

        password_segura = generate_password_hash(nueva_password)

        tienda.usuarios.update_one(
            {"email": email},
            {
                "$set": {
                    "password": password_segura
                }
            }
        )

        flash("Contraseña actualizada correctamente", "success")
        return redirect(url_for("login"))

    return render_template("restablecer.html")


@app.route("/logout")
def logout():

    session.clear()
    flash("Sesión cerrada", "success")

    return redirect(url_for("login"))

# ============ RUTAS DEL CARRITO ============

@app.route("/carrito")
def ver_carrito():
    if "usuario_id" not in session:
        flash("Inicia sesión para ver tu carrito", "warning")
        return redirect(url_for("login"))
    
    carrito = tienda.obtener_carrito(session["usuario_id"])
    return render_template("carrito.html", carrito=carrito)

@app.route("/agregar_carrito/<producto_id>", methods=["POST"])
def agregar_carrito(producto_id):
    if "usuario_id" not in session:
        flash("Inicia sesión para agregar productos al carrito", "warning")
        return redirect(url_for("login"))
    
    talla = int(request.form["talla"])
    cantidad = int(request.form.get("cantidad", 1))
    
    if tienda.agregar_al_carrito(session["usuario_id"], producto_id, talla, cantidad):
        flash("Producto agregado al carrito ✅", "success")
    else:
        flash("Error al agregar el producto", "danger")
    
    return redirect(url_for("tienda_T"))

@app.route("/quitar_carrito/<producto_id>/<int:talla>")
def quitar_carrito(producto_id, talla):
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    
    tienda.quitar_del_carrito(session["usuario_id"], producto_id, talla)
    flash("Producto eliminado del carrito", "success")
    return redirect(url_for("ver_carrito"))

@app.route("/actualizar_carrito", methods=["POST"])
def actualizar_carrito():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    
    producto_id = request.form["producto_id"]
    talla = int(request.form["talla"])
    cantidad = int(request.form["cantidad"])
    
    tienda.actualizar_cantidad(session["usuario_id"], producto_id, talla, cantidad)
    
    return redirect(url_for("ver_carrito"))

# API para el contador del carrito (NECESARIO)
@app.route("/api/carrito/count")
def api_carrito_count():
    if "usuario_id" not in session:
        return {"total_items": 0}
    
    carrito = tienda.obtener_carrito(session["usuario_id"])
    return {"total_items": carrito["total_items"]}

if __name__ == "__main__":
    app.run(debug=True)