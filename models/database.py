from contextlib import contextmanager

from exceptions.AppHttpException import AppHttpException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


class Database:
    def __init__(
        self, db_name: str, db_user: str, db_pass: str, db_host: str, db_port: int
    ):
        self.__db_name: str = db_name
        self.__db_user: str = db_user
        self.__db_pass: str = db_pass
        self.__db_host: str = db_host
        self.__db_port: str = db_port

        # DB_URL = f"mysql+pymysql://{self.__db_name}:{self.__db_pass}@{self.__db_host}:{self.__db_port}/{self.__db_name}"
        DB_URL = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

        self.engine = create_engine(DB_URL)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def execute_query(
        self,
        query,
        params: dict = {},
        fetchone: bool | None = None,
        commit: bool | None = False,
    ):
        with self.get_session() as session:
            try:
                query = text(query)
                result = session.execute(query, params)
                if commit:
                    session.commit()  # Commit the transaction
                if fetchone:
                    row = result.fetchone()
                    return dict(row._mapping) if row else None
                elif fetchone is False:
                    return [dict(row._mapping) for row in result.fetchall()]

                if hasattr(result, "lastrowid") and result.lastrowid:
                    last_inserted_id = result.lastrowid
                    return last_inserted_id
                return result.rowcount
            except Exception as e:
                session.rollback()  # Rollback the transaction in case of an error
                session.close()
                context = {
                    "error_type": type(e).__name__,
                }

                if hasattr(e, "orig"):
                    context["message"] = str(e.orig)
                if hasattr(e, "statement"):
                    context["sql"] = e.statement
                if hasattr(e, "params"):
                    context["params"] = e.params

                raise AppHttpException(
                    message="Ocurrio un error inesperado en el servidorB",
                    status_code=500,
                    context=context,
                )

    def call_procedure(self, procedure_name: str, params: list = []):
        conn = self.engine.raw_connection()
        try:
            with conn.cursor() as cursor:
                cursor.callproc(procedure_name, params)
                results = []

                # Procesar el primer result set
                if cursor.description:  # Si tiene columnas
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    results.append([dict(zip(columns, row)) for row in rows])

                # Procesar result sets adicionales
                while cursor.nextset():
                    if cursor.description:  # Si tiene columnas
                        rows = cursor.fetchall()
                        columns = [desc[0] for desc in cursor.description]
                        results.append([dict(zip(columns, row)) for row in rows])

                conn.commit()

                if not results:
                    results = False
                elif len(results) == 1:
                    results = results[0]

                return results

        except Exception as e:
            conn.rollback()
            conn.close()

            context = {
                "error_type": type(e).__name__,
            }
            context["error_code"] = str(e.args[0])
            context["message"] = str(e.args[1])

            if procedure_name:
                context["sp"] = procedure_name
            if params:
                context["params"] = params

            if e.args[0] == 1644:  # Error customizado desde MariaDB, signal 45000
                raise AppHttpException(
                    f"Ocurrio un error inesperado en el servidor: {e.args[1]}",
                    status_code=500,
                    context=context,
                )

            raise AppHttpException(
                message="Ocurrio un error inesperado en el servidorB",
                status_code=500,
                context=context,
            )

        finally:
            conn.close()

    def get_host(self):
        return self.__db_host

    def get_port(self):
        return self.__db_port

    def get_name(self):
        return self.__db_name

    def get_user(self):
        return self.__db_user
