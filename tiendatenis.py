from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime

class TiendaTenis:

    def __init__(self, uri="mongodb+srv://trabajoss159_db_user:o3RzM9YVZwd5irCZ@cluster0.2bmj0m0.mongodb.net/?appName=Cluster0"):

        try:
            self.cliente = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000
            )

            self.cliente.admin.command("ping")

            self.db = self.cliente["tienda_tenis"]

            self.usuarios = self.db["usuarios"]

            self.usuarios.create_index(
                "email",
                unique=True
            )

            print("Conectado a MongoDB")

        except ConnectionFailure:

            print("Error de conexión")
            raise

    def crear_usuario(self, nombre, email, password):

        try:

            resultado = self.usuarios.insert_one({

                "nombre": nombre,
                "email": email,
                "password": password,
                "fecha_registro": datetime.now()

            })

            return str(resultado.inserted_id)

        except DuplicateKeyError:

            print("El usuario ya existe")
            return None

    def iniciar_sesion(self, email, password):

        try:

            usuario = self.usuarios.find_one({
                "email": email
            })

            if usuario and usuario["password"] == password:

                usuario["_id"] = str(usuario["_id"])

                return usuario

            return None

        except Exception as e:

            print(e)
            return None

    def obtener_usuario(self, usuario_id):

        try:

            usuario = self.usuarios.find_one({
                "_id": ObjectId(usuario_id)
            })

            if usuario:

                usuario["_id"] = str(usuario["_id"])

                return usuario

            return None

        except Exception as e:

            print(e)
            return None