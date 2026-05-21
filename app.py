from flask import Flask, render_template, request, redirect, url_for, session, flash
from tiendatenis import TiendaTenis
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

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

    productos = tienda.obtener_productos()

    return render_template(
        "tienda.html",
        productos=productos
    )


@app.route("/agregar_producto", methods=["GET", "POST"])
def agregar_producto():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session["tipo"] != "vendedor":

        flash(
            "Solo los vendedores pueden agregar modelos",
            "warning"
        )

        return redirect(url_for("tienda_T"))

    if request.method == "POST":

        nombre = request.form["nombre"]

        marca = request.form["marca"]

        tipo = request.form["tipo"]

        color = request.form["color"]

        talla = int(request.form["talla"])

        stock = int(request.form["stock"])

        precio = float(request.form["precio"])

        condicion = request.form["condicion"]

        imagen = request.form["imagen"]

        producto_id = tienda.agregar_producto(

            nombre,
            marca,
            nombre,
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

            flash(
                "Modelo publicado correctamente",
                "success"
            )

            return redirect(url_for("tienda_T"))

        flash(
            "Error al publicar el modelo",
            "danger"
        )

        return redirect(url_for("agregar_producto"))

    return render_template("agregar_producto.html")

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

if __name__ == "__main__":
    app.run(debug=True)