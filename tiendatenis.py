from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime
from typing import Optional, List, Dict

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


class TiendaTenis:

    def __init__(
        self,
        uri: str = "mongodb+srv://trabajoss159_db_user:o3RzM9YVZwd5irCZ@cluster0.2bmj0m0.mongodb.net/?appName=Cluster0"
    ):

        try:
            self.cliente = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000
            )

            self.cliente.admin.command("ping")

            self.db = self.cliente["tienda_tenis"]

            self.usuarios = self.db["usuarios"]
            self.productos = self.db["productos"]

            self._crear_indices()

            print("Conectado a MongoDB")

        except ConnectionFailure:
            print("Error de conexión")
            raise

    def _crear_indices(self):

        self.usuarios.create_index("email", unique=True)
        self.productos.create_index("marca")
        self.productos.create_index("tipo")
        self.productos.create_index("talla")



    def crear_usuario(
        self,
        nombre: str,
        email: str,
        password: str,
        tipo: str
    ) -> Optional[str]:

        try:

            password_encriptada = generate_password_hash(password)

            resultado = self.usuarios.insert_one({
                "nombre": nombre,
                "email": email,
                "password": password_encriptada,
                "tipo": tipo,
                "fecha_registro": datetime.now(),
                "activo": True
            })

            return str(resultado.inserted_id)

        except DuplicateKeyError:
            print("El correo ya está registrado")
            return None

        except Exception as e:
            print(e)
            return None

    def iniciar_sesion(
        self,
        email: str,
        password: str
    ) -> Optional[Dict]:

        try:

            usuario = self.usuarios.find_one({"email": email})

            if not usuario:
                return None

            if check_password_hash(usuario["password"], password):

                usuario["_id"] = str(usuario["_id"])
                return usuario

            return None

        except Exception as e:
            print(e)
            return None

    def obtener_usuario(
        self,
        usuario_id: str
    ) -> Optional[Dict]:

        try:

            usuario = self.usuarios.find_one({
                "_id": ObjectId(usuario_id)
            })

            if usuario:
                usuario["_id"] = str(usuario["_id"])

            return usuario

        except Exception as e:
            print(e)
            return None

    

    def agregar_producto(
        self,
        nombre: str,
        marca: str,
        modelo: str,
        tipo: str,
        color: str,
        talla: int,
        precio: float,
        condicion: str,
        stock: int,
        id_vendedor: str
    ) -> Optional[str]:

        try:

            resultado = self.productos.insert_one({
                "nombre": nombre,
                "marca": marca,
                "modelo": modelo,
                "tipo": tipo,
                "color": color,
                "talla": talla,
                "precio": precio,
                "condicion": condicion,
                "stock": stock,
                "id_vendedor": ObjectId(id_vendedor),
                "fecha_publicacion": datetime.now(),
                "activo": True
            })

            return str(resultado.inserted_id)

        except Exception as e:
            print(e)
            return None

    def obtener_productos(self) -> List[Dict]:

        productos = self.productos.find({
            "activo": True
        }).sort("fecha_publicacion", -1)

        resultado = []

        for producto in productos:
            producto["_id"] = str(producto["_id"])
            producto["id_vendedor"] = str(producto["id_vendedor"])
            resultado.append(producto)

        return resultado