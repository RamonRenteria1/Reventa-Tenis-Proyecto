from flask import Flask, render_template, request, redirect, url_for, session, flash
from tiendatenis import TiendaTenis
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from bson.objectid import ObjectId
from datetime import datetime
import re

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
        session["username"] = usuario.get("username", "usuario")
        session["foto_perfil"] = usuario.get("foto_perfil", "")
        session["tipo"] = usuario["tipo"]

        flash("Bienvenido", "success")
        return redirect(url_for("tienda_T"))

    return render_template("login.html")

@app.route("/registro", methods=["GET", "POST"])
def registro():

    if request.method == "POST":

        nombre = request.form["nombre"]
        username = request.form["username"]
        email = request.form["email"]
        telefono = request.form.get("telefono", "")
        foto_perfil = request.form.get("foto_perfil", "")

        password_original = request.form["password"]
        confirmar_password = request.form["confirmar_password"]

        tipo = "comprador"

        if password_original != confirmar_password:
            flash("Las contraseñas no coinciden", "danger")
            return redirect(url_for("registro"))

        patron_password = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).+$"

        if not re.match(patron_password, password_original):
            flash("La contraseña debe tener al menos una mayúscula, una minúscula y un carácter especial", "warning")
            return redirect(url_for("registro"))

        usuario_id = tienda.crear_usuario(
            nombre,
            email,
            password_original,
            tipo,
            username,
            foto_perfil,
            telefono
        )

        if not usuario_id:
            flash("El usuario ya existe", "danger")
            return redirect(url_for("registro"))

        flash("Usuario registrado correctamente", "success")
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

    for producto in productos:
        vendedor = tienda.usuarios.find_one({
            "_id": ObjectId(producto["id_vendedor"])
        })

        if vendedor:
            producto["telefono_vendedor"] = vendedor.get("telefono", "")
            producto["nombre_vendedor"] = vendedor.get("nombre", "Vendedor")
            producto["username_vendedor"] = vendedor.get("username", "vendedor")
        else:
            producto["telefono_vendedor"] = ""
            producto["nombre_vendedor"] = "Vendedor"
            producto["username_vendedor"] = "vendedor"

    return render_template(
        "tienda.html",
        productos=productos
    )

@app.route("/admin")
def admin_dashboard():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("tipo") != "admin":
        flash("No tienes permiso para entrar al panel de administrador", "danger")
        return redirect(url_for("tienda_T"))

    total_usuarios = tienda.usuarios.count_documents({})
    total_productos = tienda.productos.count_documents({"activo": True})
    total_carritos = tienda.carritos.count_documents({})

    usuarios = list(tienda.usuarios.find().sort("fecha_registro", -1))
    productos = list(tienda.productos.find().sort("fecha_publicacion", -1))

    for usuario in usuarios:
        usuario["_id"] = str(usuario["_id"])

    for producto in productos:
        producto["_id"] = str(producto["_id"])
        producto["id_vendedor"] = str(producto["id_vendedor"])

    return render_template(
        "admin_dashboard.html",
        total_usuarios=total_usuarios,
        total_productos=total_productos,
        total_carritos=total_carritos,
        usuarios=usuarios,
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
        username = request.form["username"].strip().lower()
        email = request.form["email"].strip().lower()
        telefono = request.form.get("telefono", "").strip()
        foto_perfil = request.form.get("foto_perfil", "").strip()

        if not nombre or not username or not email:
            flash("Nombre, usuario y correo son obligatorios", "warning")
            return redirect(url_for("editar_perfil"))

        correo_existente = tienda.usuarios.find_one({
            "email": email,
            "_id": {"$ne": ObjectId(session["usuario_id"])}
        })

        if correo_existente:
            flash("El correo ya está en uso", "danger")
            return redirect(url_for("editar_perfil"))

        username_existente = tienda.usuarios.find_one({
            "username": username,
            "_id": {"$ne": ObjectId(session["usuario_id"])}
        })

        if username_existente:
            flash("Ese nombre de usuario ya está en uso", "danger")
            return redirect(url_for("editar_perfil"))

        tienda.usuarios.update_one(
            {"_id": ObjectId(session["usuario_id"])},
            {
                "$set": {
                    "nombre": nombre,
                    "username": username,
                    "email": email,
                    "telefono": telefono,
                    "foto_perfil": foto_perfil
                }
            }
        )

        session["nombre"] = nombre
        session["username"] = username
        session["foto_perfil"] = foto_perfil

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


@app.route("/api/carrito/count")
def api_carrito_count():
    if "usuario_id" not in session:
        return {"total_items": 0}
    
    carrito = tienda.obtener_carrito(session["usuario_id"])
    return {"total_items": carrito["total_items"]}

@app.route("/mis_publicaciones")
def mis_publicaciones():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("tipo") != "vendedor":
        flash("Solo los vendedores pueden ver sus publicaciones", "warning")
        return redirect(url_for("tienda_T"))

    productos = list(tienda.productos.find({
        "id_vendedor": ObjectId(session["usuario_id"])
    }).sort("fecha_publicacion", -1))

    total_publicaciones = len(productos)
    productos_activos = sum(1 for producto in productos if producto.get("activo", True))
    productos_vendidos = sum(1 for producto in productos if producto.get("stock", 0) <= 0)
    stock_total = sum(producto.get("stock", 0) for producto in productos if producto.get("activo", True))

    for producto in productos:
        producto["_id"] = str(producto["_id"])
        producto["id_vendedor"] = str(producto["id_vendedor"])

    return render_template(
        "mis_publicaciones.html",
        productos=productos,
        total_publicaciones=total_publicaciones,
        productos_activos=productos_activos,
        productos_vendidos=productos_vendidos,
        stock_total=stock_total
    )
    
@app.route("/checkout")
def checkout():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    carrito = tienda.obtener_carrito(session["usuario_id"])

    if carrito["total_items"] <= 0:
        flash("Tu carrito está vacío", "warning")
        return redirect(url_for("ver_carrito"))

    return render_template("checkout.html", carrito=carrito)


@app.route("/confirmar_compra", methods=["POST"])
def confirmar_compra():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    carrito = tienda.obtener_carrito(session["usuario_id"])

    if carrito["total_items"] <= 0:
        flash("Tu carrito está vacío", "warning")
        return redirect(url_for("ver_carrito"))

    direccion = request.form["direccion"].strip()
    telefono = request.form["telefono"].strip()
    metodo_pago = request.form["metodo_pago"]

    if not direccion or not telefono:
        flash("Dirección y teléfono son obligatorios", "warning")
        return redirect(url_for("checkout"))

    pedido = {
        "usuario_id": session["usuario_id"],
        "nombre_cliente": session.get("nombre", ""),
        "items": carrito["items"],
        "total_items": carrito["total_items"],
        "total_precio": carrito["total_precio"],
        "direccion": direccion,
        "telefono": telefono,
        "metodo_pago": metodo_pago,
        "estado": "Confirmado",
        "fecha_pedido": datetime.now()
    }

    tienda.pedidos.insert_one(pedido)

    tienda.carritos.update_one(
        {"usuario_id": session["usuario_id"]},
        {
            "$set": {
                "items": [],
                "total_items": 0,
                "total_precio": 0,
                "updated_at": datetime.now()
            }
        }
    )

    flash("Compra confirmada correctamente", "success")
    return redirect(url_for("mis_pedidos"))


@app.route("/mis_pedidos")
def mis_pedidos():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    pedidos = list(tienda.pedidos.find({
        "usuario_id": session["usuario_id"]
    }).sort("fecha_pedido", -1))

    for pedido in pedidos:
        pedido["_id"] = str(pedido["_id"])

    return render_template("mis_pedidos.html", pedidos=pedidos)

@app.route("/pedidos_vendedor")
def pedidos_vendedor():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("tipo") != "vendedor":
        flash("Solo los vendedores pueden ver sus pedidos", "warning")
        return redirect(url_for("tienda_T"))

    pedidos = list(tienda.pedidos.find({
        "items.vendedor_id": session["usuario_id"]
    }).sort("fecha_pedido", -1))

    pedidos_filtrados = []

    for pedido in pedidos:
        items_vendedor = []

        for item in pedido.get("items", []):
            if item.get("vendedor_id") == session["usuario_id"]:
                items_vendedor.append(item)

        if items_vendedor:
            total_vendedor = sum(
                item["precio"] * item["cantidad"]
                for item in items_vendedor
            )

            pedido["_id"] = str(pedido["_id"])
            pedido["items_vendedor"] = items_vendedor
            pedido["total_vendedor"] = total_vendedor

            pedidos_filtrados.append(pedido)

    return render_template(
        "pedidos_vendedor.html",
        pedidos=pedidos_filtrados
    )
    
@app.route("/solicitar_vendedor", methods=["POST"])
def solicitar_vendedor():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario = tienda.obtener_usuario(session["usuario_id"])

    if not usuario:
        return redirect(url_for("login"))

    if usuario.get("tipo") == "vendedor":
        flash("Ya eres vendedor", "info")
        return redirect(url_for("perfil"))

    motivo = request.form.get("motivo_solicitud", "").strip()

    if not motivo:
        flash("Debes escribir un motivo para solicitar ser vendedor", "warning")
        return redirect(url_for("perfil"))

    tienda.usuarios.update_one(
        {"_id": ObjectId(session["usuario_id"])},
        {
            "$set": {
                "solicitud_vendedor": "pendiente",
                "motivo_solicitud_vendedor": motivo,
                "fecha_solicitud_vendedor": datetime.now()
            }
        }
    )

    flash("Solicitud enviada. Un administrador debe aprobarte.", "success")
    return redirect(url_for("perfil"))

@app.route("/aprobar_vendedor/<usuario_id>", methods=["POST"])
def aprobar_vendedor(usuario_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("tipo") != "admin":
        flash("No tienes permiso", "danger")
        return redirect(url_for("tienda_T"))

    tienda.usuarios.update_one(
        {"_id": ObjectId(usuario_id)},
        {
            "$set": {
                "tipo": "vendedor",
                "solicitud_vendedor": "aprobada"
            }
        }
    )

    flash("Solicitud aprobada. El usuario debe cerrar sesión y volver a entrar.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/rechazar_vendedor/<usuario_id>", methods=["POST"])
def rechazar_vendedor(usuario_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("tipo") != "admin":
        flash("No tienes permiso", "danger")
        return redirect(url_for("tienda_T"))

    tienda.usuarios.update_one(
        {"_id": ObjectId(usuario_id)},
        {
            "$set": {
                "solicitud_vendedor": "rechazada"
            }
        }
    )

    flash("Solicitud rechazada", "warning")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    app.run(debug=True)