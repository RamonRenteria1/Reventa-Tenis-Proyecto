from flask import Flask, render_template, request, redirect, url_for, session, flash
from tiendatenis import TiendaTenis

app = Flask(__name__)
app.secret_key = "clave"


tienda = TiendaTenis()


@app.route("/")
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        usuario = tienda.iniciar_sesion(
            email,
            password
        )

        if not usuario:

            flash("Correo o contraseña incorrectos")
            return redirect(url_for("login"))

        session["usuario_id"] = usuario["_id"]
        session["nombre"] = usuario["nombre"]

        flash("Bienvenido")
        return redirect(url_for("index"))

    return render_template("login.html")




@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        nombre = request.form["nombre"]
        email = request.form["email"]
        password = request.form["password"]

        usuario_id = tienda.crear_usuario(
            nombre,
            email,
            password
        )

        if not usuario_id:

            flash("El usuario ya existe")
            return redirect(url_for("register"))

        flash("Usuario registrado correctamente")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def index():
    return render_template("index")



@app.route("/logout")
def logout():

    session.clear()

    flash("Sesión cerrada")

    return redirect(url_for("index"))

# RUN
if __name__ == "__main__":
    app.run(debug=True)