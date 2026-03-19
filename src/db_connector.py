"""Conector a base de datos Firebird de Microsip."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import pandas as pd

logger = logging.getLogger(__name__)


class FirebirdConnector:
    """Clase para establecer y gestionar la conexión a la base de datos Firebird.

    Esta clase detecta automáticamente el driver disponible, gestiona la
    conexión de forma segura y provee métodos para ejecutar consultas SQL simples.
    Está diseñada para ser tolerante a fallos y escalable a nivel empresarial.

    Attributes:
        config (dict[str, str | int]): Diccionario con las credenciales y
            parámetros de conexión a la base de datos.
    """

    def __init__(self, config: dict[str, str | int]) -> None:
        """Inicializa el conector con la configuración proporcionada.

        Args:
            config (dict[str, str | int]): Diccionario de configuración con
                claves como 'host', 'port', 'database', 'user', 'password' y 'charset'.
        """
        self.config = config
        self._driver: str = self._detect_driver()

    @staticmethod
    def _detect_driver() -> str:
        """Detecta el driver de Firebird instalado en el entorno.

        Busca primero 'firebird-driver' (para versiones recientes) y luego 'fdb'
        (para Firebird 2.5).

        Returns:
            str: El nombre del driver detectado ('firebird-driver' o 'fdb').

        Raises:
            ImportError: Si no se encuentra ninguno de los drivers requeridos.
        """
        try:
            import firebird.driver  # noqa: F401
            return "firebird-driver"
        except ImportError:
            pass
        try:
            import fdb  # noqa: F401
            return "fdb"
        except ImportError:
            pass
        raise ImportError(
            "No se encontró driver de Firebird. Instala uno:\n"
            "  pip install firebird-driver   (Firebird 3+/4+)\n"
            "  pip install fdb               (Firebird 2.5)\n"
        )

    @contextmanager
    def connect(self) -> Generator[Any, None, None]:
        """Proporciona un contexto seguro para la conexión a la base de datos.

        Maneja la apertura y el cierre automático de la conexión, asegurando
        que los recursos se liberen incluso si ocurren excepciones.

        Yields:
            Any: El objeto de conexión activa a la base de datos.

        Raises:
            Exception: Si ocurre un error al intentar establecer la conexión.
        """
        conn: Any = None
        try:
            if self._driver == "firebird-driver":
                from firebird.driver import connect as fb_connect
                host = self.config["host"]
                port = self.config.get("port", 3050)
                database = self.config["database"]
                dsn = f"{host}/{port}:{database}"
                conn = fb_connect(
                    dsn,
                    user=self.config["user"],
                    password=self.config["password"],
                    charset=self.config.get("charset", "WIN1252"),
                )
            else:
                import fdb
                conn = fdb.connect(
                    host=self.config["host"],
                    port=self.config.get("port", 3050),
                    database=self.config["database"],
                    user=self.config["user"],
                    password=self.config["password"],
                    charset=self.config.get("charset", "WIN1252"),
                )
            logger.info("Conexión a Firebird establecida: %s", self.config["database"])
            yield conn
        except Exception as e:
            logger.error("Error de conexión a Firebird: %s", e)
            raise
        finally:
            if conn is not None:
                conn.close()
                logger.info("Conexión a Firebird cerrada.")

    def execute_query(self, sql: str) -> pd.DataFrame:
        """Ejecuta una consulta SQL y devuelve los resultados en un DataFrame.

        Args:
            sql (str): La cadena de la consulta SQL a ejecutar. Debe ser
                preferentemente una consulta de selección simple para ocultar
                lógica de negocio.

        Returns:
            pd.DataFrame: Un DataFrame de pandas con los resultados de la consulta.
        """
        with self.connect() as conn:
            logger.info("Ejecutando consulta (%d caracteres)...", len(sql))
            cursor = conn.cursor()
            cursor.execute(sql)
            cols = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()
            df = pd.DataFrame(rows, columns=cols)
            logger.info("Consulta ejecutada - %d filas x %d columnas", *df.shape)
        return df

    def execute_sql_file(self, sql_path: str | Path) -> pd.DataFrame:
        """Lee y ejecuta el contenido de un archivo SQL.

        Args:
            sql_path (str | Path): Ruta al archivo SQL a ejecutar.

        Returns:
            pd.DataFrame: Resultados de la consulta.

        Raises:
            FileNotFoundError: Si la ruta del archivo no existe.
        """
        sql_path = Path(sql_path)
        if not sql_path.exists():
            raise FileNotFoundError(f"Archivo SQL no encontrado: {sql_path}")
        sql = sql_path.read_text(encoding="utf-8")
        logger.info("Archivo SQL cargado: %s", sql_path.name)
        return self.execute_query(sql)

    def extract_table(self, table_name: str, columns: list[str] | None = None) -> pd.DataFrame:
        """Extrae datos de una tabla específica utilizando una consulta simple.

        Este método oculta la lógica de negocio al administrador de la base de
        datos, ya que solo realiza consultas planas (SELECT) sin JOINs complejos.

        Args:
            table_name (str): El nombre de la tabla en la base de datos.
            columns (list[str] | None, optional): Lista de columnas a extraer.
                Si es None, se extraerán todas las columnas (*).

        Returns:
            pd.DataFrame: DataFrame con los datos extraídos de la tabla.
        """
        cols_str = ", ".join(columns) if columns else "*"
        sql = f"SELECT {cols_str} FROM {table_name}"
        logger.info("Extrayendo tabla: %s", table_name)
        return self.execute_query(sql)

    def test_connection(self) -> bool:
        """Verifica que la conexión a la base de datos sea exitosa.

        Ejecuta una consulta de prueba muy ligera para confirmar la conectividad.

        Returns:
            bool: True si la conexión es exitosa, False en caso contrario.
        """
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM RDB$DATABASE")
                cursor.fetchone()
                cursor.close()
            logger.info("Prueba de conexión exitosa.")
            return True
        except Exception as e:
            logger.error("Prueba de conexión fallida: %s", e)
            return False