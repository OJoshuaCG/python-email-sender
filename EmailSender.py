import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Dict, Optional, Union
import aiosmtplib
from jinja2 import Template
from mjml import mjml_to_html
import os
from dotenv import load_dotenv

load_dotenv()


class EmailSender:
    """
    Clase para envío asíncrono de correos electrónicos con soporte para:
    - Templates MJML
    - Variables dinámicas con Jinja2
    - Archivos adjuntos
    - Envío asíncrono
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        use_tls: bool = True,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ):
        """
        Inicializa el cliente de correo electrónico.

        Args:
            smtp_host: Servidor SMTP (ej: 'smtp.gmail.com')
            smtp_port: Puerto SMTP (ej: 587 para TLS, 465 para SSL)
            username: Usuario SMTP
            password: Contraseña SMTP
            use_tls: Si se debe usar TLS (default: True)
            from_email: Email del remitente (default: username)
            from_name: Nombre del remitente (opcional)
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_email = from_email or username
        self.from_name = from_name

    def _load_mjml_template(self, template_path: Union[str, Path]) -> str:
        """
        Carga un archivo MJML desde el sistema de archivos.

        Args:
            template_path: Ruta al archivo MJML

        Returns:
            Contenido del template MJML
        """
        path = Path(template_path)
        if not path.exists():
            raise FileNotFoundError(f"Template no encontrado: {template_path}")

        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _render_template(self, mjml_content: str, variables: Dict[str, any]) -> str:
        """
        Renderiza un template MJML con variables Jinja2 y lo convierte a HTML.

        Args:
            mjml_content: Contenido del template MJML
            variables: Diccionario con variables para reemplazar

        Returns:
            HTML renderizado
        """
        # Paso 1: Renderizar variables con Jinja2
        jinja_template = Template(mjml_content)
        mjml_rendered = jinja_template.render(**variables)

        # Paso 2: Convertir MJML a HTML
        html_result = mjml_to_html(mjml_rendered)

        if html_result.get("errors"):
            raise ValueError(f"Errores en MJML: {html_result['errors']}")

        return html_result["html"]

    def _create_message(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        attachments: Optional[List[Union[str, Path]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> MIMEMultipart:
        """
        Crea el mensaje de correo electrónico.

        Args:
            to_email: Email del destinatario
            subject: Asunto del correo
            html_content: Contenido HTML del correo
            attachments: Lista de rutas a archivos adjuntos
            cc: Lista de emails en copia
            bcc: Lista de emails en copia oculta

        Returns:
            Objeto MIMEMultipart con el mensaje construido
        """
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["To"] = to_email

        if self.from_name:
            msg["From"] = f"{self.from_name} <{self.from_email}>"
        else:
            msg["From"] = self.from_email

        if cc:
            msg["Cc"] = ", ".join(cc)
        if bcc:
            msg["Bcc"] = ", ".join(bcc)

        # Agregar contenido HTML
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        # Agregar archivos adjuntos
        if attachments:
            for attachment_path in attachments:
                self._attach_file(msg, attachment_path)

        return msg

    def _attach_file(self, msg: MIMEMultipart, file_path: Union[str, Path]) -> None:
        """
        Adjunta un archivo al mensaje.

        Args:
            msg: Mensaje al que se adjuntará el archivo
            file_path: Ruta al archivo a adjuntar
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        with open(path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())

        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename= {path.name}")

        msg.attach(part)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        template_path: Union[str, Path],
        variables: Dict[str, any],
        attachments: Optional[List[Union[str, Path]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        Envía un correo electrónico de forma asíncrona.

        Args:
            to_email: Email del destinatario
            subject: Asunto del correo
            template_path: Ruta al template MJML
            variables: Variables para renderizar en el template
            attachments: Lista de archivos adjuntos
            cc: Lista de emails en copia
            bcc: Lista de emails en copia oculta

        Returns:
            True si el envío fue exitoso, False en caso contrario
        """
        try:
            # Cargar y renderizar template
            mjml_content = self._load_mjml_template(template_path)
            html_content = self._render_template(mjml_content, variables)

            # Crear mensaje
            msg = self._create_message(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                attachments=attachments,
                cc=cc,
                bcc=bcc,
            )

            # Enviar correo de forma asíncrona
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls,
            )

            return True

        except Exception as e:
            print(f"Error al enviar correo a {to_email}: {str(e)}")
            return False

    async def send_bulk_emails(
        self,
        recipients: List[Dict[str, any]],
        subject: str,
        template_path: Union[str, Path],
        attachments: Optional[List[Union[str, Path]]] = None,
    ) -> Dict[str, List[str]]:
        """
        Envía correos masivos personalizados de forma asíncrona.

        Args:
            recipients: Lista de diccionarios con 'email' y 'variables' para cada destinatario
                Ejemplo: [
                    {'email': 'user@example.com', 'variables': {'name': 'Juan', 'code': '123'}},
                    {'email': 'otro@example.com', 'variables': {'name': 'María', 'code': '456'}}
                ]
            subject: Asunto del correo (puede contener variables con {variable})
            template_path: Ruta al template MJML
            attachments: Lista de archivos adjuntos (común para todos)

        Returns:
            Diccionario con listas de 'success' y 'failed' con los emails
        """
        tasks = []

        for recipient in recipients:
            email = recipient["email"]
            variables = recipient.get("variables", {})

            # Renderizar subject con variables si las tiene
            rendered_subject = (
                subject.format(**variables) if "{" in subject else subject
            )

            task = self.send_email(
                to_email=email,
                subject=rendered_subject,
                template_path=template_path,
                variables=variables,
                attachments=attachments,
            )
            tasks.append((email, task))

        # Ejecutar todas las tareas en paralelo
        results = await asyncio.gather(
            *[task for _, task in tasks], return_exceptions=True
        )

        # Clasificar resultados
        success = []
        failed = []

        for (email, _), result in zip(tasks, results):
            if result is True:
                success.append(email)
            else:
                failed.append(email)

        return {"success": success, "failed": failed}


# Ejemplo de uso
async def main():
    # Configurar el cliente de correo
    email_sender = EmailSender(
        smtp_host=os.getenv("EMAIL_HOST"),
        smtp_port=os.getenv("EMAIL_PORT"),
        username=os.getenv("EMAIL_USER"),
        password=os.getenv("EMAIL_PASSWORD"),
        from_name=os.getenv("EMAIL_FROM_NAME"),
    )

    # Ejemplo 1: Enviar un correo individual
    success = await email_sender.send_email(
        to_email="destinatario@example.com",
        subject="Bienvenido a nuestra plataforma",
        template_path="templates/welcome.mjml",
        variables={
            "nombre": "Juan Pérez",
            "codigo_activacion": "ABC123",
            "fecha": "06 de Octubre, 2025",
        },
        attachments=["documents/example.pdf"],
    )

    if success:
        print("Correo enviado exitosamente")

    # Ejemplo 2: Enviar correos masivos personalizados
    recipients = [
        {
            "email": "usuario1@example.com",
            "variables": {"nombre": "María", "saldo": "1,250.00"},
        },
        {
            "email": "usuario2@example.com",
            "variables": {"nombre": "Carlos", "saldo": "3,500.00"},
        },
        {
            "email": "usuario3@example.com",
            "variables": {"nombre": "Ana", "saldo": "890.00"},
        },
    ]

    results = await email_sender.send_bulk_emails(
        recipients=recipients,
        subject="Estado de cuenta - {nombre}",
        template_path="templates/estado_cuenta.mjml",
        attachments=["documentos/terminos.pdf"],
    )

    print(f"Enviados: {len(results['success'])}")
    print(f"Fallidos: {len(results['failed'])}")


# Ejecutar el ejemplo
if __name__ == "__main__":
    asyncio.run(main())
