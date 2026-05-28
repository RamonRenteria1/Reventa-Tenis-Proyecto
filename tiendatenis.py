from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime
from typing import Optional, List, Dict
from werkzeug.security import generate_password_hash, check_password_hash


class TiendaTenis:

    def __init__(
        self,
        uri: str = "mongodb+srv://trabajoss159_db_user:o3RzM9YVZwd5irCZ@cluster0.2bmj0m0.mongodb.net/?appName=Cluster0",
    ):
        """Inicializar conexión a MongoDB Atlas"""

        try:
            self.cliente = MongoClient(uri, serverSelectionTimeoutMS=5000)

            self.cliente.admin.command("ping")

            self.db = self.cliente["tienda_tenis"]

            self.usuarios = self.db["usuarios"]
            self.productos = self.db["productos"]
            self.carritos = self.db["carritos"]
            self.pedidos = self.db["pedidos"]

            self._crear_indices()

            print("✅ Conectado a MongoDB")

        except ConnectionFailure:
            print("❌ Error: No se pudo conectar a MongoDB")
            raise

    def _crear_indices(self):
        """Crear índices para mejorar rendimiento"""

        self.usuarios.create_index("email", unique=True)
        self.productos.create_index([("id_vendedor", 1), ("fecha_publicacion", -1)])
        self.productos.create_index("marca")
        self.productos.create_index("tipo")
        self.productos.create_index("talla")
        self.productos.create_index("activo")
        self.carritos.create_index("usuario_id", unique=True)
        self.pedidos.create_index("usuario_id")
        self.pedidos.create_index("fecha_pedido")

    def crear_usuario(
        self,
        nombre: str,
        email: str,
        password: str,
        tipo: str,
        username: str = "",
        foto_perfil: str = "",
        telefono: str = ""
    ) -> Optional[str]:
        """Crear un nuevo usuario comprador o vendedor"""

        try:
            password_encriptada = generate_password_hash(password)

            resultado = self.usuarios.insert_one({
                "nombre": nombre,
                "username": username,
                "email": email,
                "password": password_encriptada,
                "tipo": tipo,
                "foto_perfil": foto_perfil,
                "telefono": telefono,
                "fecha_registro": datetime.now(),
                "activo": True
            })

            return str(resultado.inserted_id)

        except DuplicateKeyError:
            print("❌ Error: usuario o correo ya registrado")
            return None

        except Exception as e:
            print(f"Error al crear usuario: {e}")
            return None

    def iniciar_sesion(
        self,
        email: str,
        password: str
    ) -> Optional[Dict]:
        """Buscar usuario por email y validar contraseña"""

        try:
            usuario = self.usuarios.find_one({
                "email": email,
                "activo": True
            })

            if not usuario:
                return None

            if check_password_hash(usuario["password"], password):
                usuario["_id"] = str(usuario["_id"])
                return usuario

            return None

        except Exception as e:
            print(f"Error al iniciar sesión: {e}")
            return None

    def obtener_usuario(
        self,
        usuario_id: str
    ) -> Optional[Dict]:
        """Obtener usuario por ID"""

        try:
            usuario = self.usuarios.find_one({
                "_id": ObjectId(usuario_id)
            })

            if usuario:
                usuario["_id"] = str(usuario["_id"])

            return usuario

        except Exception as e:
            print(f"Error al obtener usuario: {e}")
            return None

    def crear_producto(
        self,
        usuario_id: str,
        nombre: str,
        marca: str,
        modelo: str,
        tipo: str,
        color: str,
        talla: int,
        precio: float,
        condicion: str,
        stock: int,
        imagen: str = ""
    ) -> Optional[str]:
        """Crear un nuevo producto/modelo para un vendedor"""

        if not self.obtener_usuario(usuario_id):
            print(f"❌ Error: Usuario {usuario_id} no existe")
            return None

        producto = {
            "id_vendedor": ObjectId(usuario_id),
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
            "fecha_publicacion": datetime.now(),
            "activo": True
        }

        try:
            resultado = self.productos.insert_one(producto)
            return str(resultado.inserted_id)

        except Exception as e:
            print(f"Error al crear producto: {e}")
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
        id_vendedor: str,
        imagen: str
    ) -> Optional[str]:
        """Alias para mantener compatible tu app.py actual"""

        return self.crear_producto(
            id_vendedor,
            nombre,
            marca,
            modelo,
            tipo,
            color,
            talla,
            precio,
            condicion,
            stock,
            imagen
        )

    def obtener_productos(self, filtros: Optional[Dict] = None) -> List[Dict]:
        """Obtener productos activos y opcionalmente aplicar filtros"""

        try:
            query = {"activo": True}

            if filtros:
                query.update(filtros)

            productos = self.productos.find(query).sort("fecha_publicacion", -1)

            resultado = []

            for producto in productos:
                producto["_id"] = str(producto["_id"])
                producto["id_vendedor"] = str(producto["id_vendedor"])
                resultado.append(producto)

            return resultado

        except Exception as e:
            print(f"Error al obtener productos: {e}")
            return []

    def obtener_productos_vendedor(
        self,
        usuario_id: str
    ) -> List[Dict]:
        """Obtener productos publicados por un vendedor"""

        try:
            productos = self.productos.find({
                "id_vendedor": ObjectId(usuario_id),
                "activo": True
            }).sort("fecha_publicacion", -1)

            resultado = []

            for producto in productos:
                producto["_id"] = str(producto["_id"])
                producto["id_vendedor"] = str(producto["id_vendedor"])
                resultado.append(producto)

            return resultado

        except Exception as e:
            print(f"Error al obtener productos del vendedor: {e}")
            return []

    def obtener_carrito(self, usuario_id: str):
        """Obtiene el carrito del usuario o crea uno nuevo"""

        carrito = self.carritos.find_one({
            "usuario_id": usuario_id
        })

        if not carrito:
            carrito = {
                "usuario_id": usuario_id,
                "items": [],
                "total_items": 0,
                "total_precio": 0,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }

            result = self.carritos.insert_one(carrito)
            carrito["_id"] = result.inserted_id

        else:
            if not isinstance(carrito.get("items"), list):
                carrito["items"] = (
                    list(carrito.get("items", []))
                    if carrito.get("items")
                    else []
                )

        return carrito

    def agregar_al_carrito(self, usuario_id: str, producto_id: str, talla: int, cantidad: int = 1) -> bool:
        if cantidad <= 0:
            return False

        producto = self.productos.find_one({
            "_id": ObjectId(producto_id),
            "activo": True
        })

        if not producto:
            return False

        stock_disponible = int(producto.get("stock", 0))

        if stock_disponible < cantidad:
            return False

        self.productos.update_one(
            {"_id": ObjectId(producto_id)},
            {"$inc": {"stock": -cantidad}}
        )

        carrito = self.obtener_carrito(usuario_id)

        item_existente = None

        for item in carrito["items"]:
            if item["producto_id"] == producto_id and item["talla"] == talla:
                item_existente = item
                break

        if item_existente:
            item_existente["cantidad"] += cantidad
        else:
            carrito["items"].append({
                "producto_id": producto_id,
                "nombre": producto["nombre"],
                "marca": producto["marca"],
                "talla": talla,
                "cantidad": cantidad,
                "precio": producto["precio"],
                "imagen": producto.get("imagen", ""),
                "vendedor_id": str(producto["id_vendedor"])
            })

        total_items = sum(item["cantidad"] for item in carrito["items"])
        total_precio = sum(item["cantidad"] * item["precio"] for item in carrito["items"])

        self.carritos.update_one(
            {"usuario_id": usuario_id},
            {
                "$set": {
                    "items": carrito["items"],
                    "total_items": total_items,
                    "total_precio": total_precio,
                    "updated_at": datetime.now()
                }
            }
        )

        return True

    def quitar_del_carrito(self, usuario_id: str, producto_id: str, talla: int) -> bool:

        carrito = self.obtener_carrito(usuario_id)

        item_eliminado = None

        for item in carrito["items"]:
            if item["producto_id"] == producto_id and item["talla"] == talla:
                item_eliminado = item
                break

        if not item_eliminado:
            return False

        self.productos.update_one(
            {"_id": ObjectId(producto_id)},
            {"$inc": {"stock": item_eliminado["cantidad"]}}
        )

        carrito["items"] = [
            item for item in carrito["items"]
            if not (item["producto_id"] == producto_id and item["talla"] == talla)
        ]

        total_items = sum(item["cantidad"] for item in carrito["items"])
        total_precio = sum(item["cantidad"] * item["precio"] for item in carrito["items"])

        self.carritos.update_one(
            {"usuario_id": usuario_id},
            {
                "$set": {
                    "items": carrito["items"],
                    "total_items": total_items,
                    "total_precio": total_precio,
                    "updated_at": datetime.now()
                }
            }
        )

        return True

    def actualizar_cantidad(self, usuario_id: str, producto_id: str, talla: int, cantidad: int) -> bool:

        if cantidad <= 0:
            return self.quitar_del_carrito(usuario_id, producto_id, talla)

        carrito = self.obtener_carrito(usuario_id)

        item_existente = None

        for item in carrito["items"]:
            if item["producto_id"] == producto_id and item["talla"] == talla:
                item_existente = item
                break

        if not item_existente:
            return False

        cantidad_actual = item_existente["cantidad"]
        diferencia = cantidad - cantidad_actual

        producto = self.productos.find_one({"_id": ObjectId(producto_id)})
        stock_disponible = int(producto.get("stock", 0)) if producto else 0

        if diferencia > 0 and stock_disponible < diferencia:
            return False

        if diferencia != 0:
            self.productos.update_one(
                {"_id": ObjectId(producto_id)},
                {"$inc": {"stock": -diferencia}}
            )

        item_existente["cantidad"] = cantidad

        total_items = sum(item["cantidad"] for item in carrito["items"])
        total_precio = sum(item["cantidad"] * item["precio"] for item in carrito["items"])

        self.carritos.update_one(
            {"usuario_id": usuario_id},
            {
                "$set": {
                    "items": carrito["items"],
                    "total_items": total_items,
                    "total_precio": total_precio,
                    "updated_at": datetime.now()
                }
            }
        )

        return True

    def cerrar_conexion(self):
        """Cerrar conexión a MongoDB"""

        if self.cliente:
            self.cliente.close()
            print("🔌 Conexión cerrada")