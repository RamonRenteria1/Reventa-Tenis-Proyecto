from flask import Flask, render_template, request, redirect, url_for, session, flash
from tiendatenis import TiendaTenis
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "clave"

tienda = TiendaTenis()


@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        usuario = tienda.iniciar_sesion(
            email,
            password
        )

        if not usuario:
            flash("Correo o contraseña incorrectos","danger")
            return redirect(url_for("login"))

        session["usuario_id"] = usuario["_id"]
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
        flash("Solo los vendedores pueden agregar productos", "danger")
        return redirect(url_for("tienda_page"))

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

        producto_id = tienda.agregar_producto(
            nombre,
            marca,
            modelo,
            tipo,
            color,
            talla,
            precio,
            condicion,
            stock,
            session["usuario_id"]
        )

        if producto_id:
            flash("Producto agregado correctamente", "success")
            return redirect(url_for("tienda_page"))

        flash("Error al agregar producto")
        return redirect(url_for("agregar_producto"))

    return render_template("agregar_producto.html")


@app.route("/recuperar")
def recuperar():

    return render_template("recuperar.html")


@app.route("/logout")
def logout():

    session.clear()
    flash("Sesión cerrada", "success")

    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)