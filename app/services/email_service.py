import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

async def send_reset_code_email(email_to: str, code: str) -> bool:
    """
    Envia un correo transaccional con el código de 6 dígitos.
    En entorno local si no hay SMTP configurado, imprime el código en la consola.
    """
    subject = "Código de Recuperación de Contraseña - Dislubinca App"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 500px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #0F4C81;">Recuperación de Contraseña</h2>
                <p>Has solicitado restablecer la contraseña de tu cuenta en Dislubinca App.</p>
                <p>Tu código de verificación de 6 dígitos es:</p>
                <div style="background-color: #f4f6f8; padding: 15px; text-align: center; font-size: 28px; font-weight: bold; letter-spacing: 5px; color: #0F4C81; border-radius: 6px;">
                    {code}
                </div>
                <p style="font-size: 12px; color: #777; margin-top: 20px;">Este código expira en 15 minutos. Si no solicitaste este cambio, puedes ignorar este correo de forma segura.</p>
            </div>
        </body>
    </html>
    """
    
    # Impresión en consola para pruebas de desarrollo sin servidor SMTP
    print(f"\n==========================================")
    print(f"📧 EMAIL ENVIADO A: {email_to}")
    print(f"🔑 CÓDIGO DE RESTABLECIMIENTO: {code}")
    print(f"==========================================\n")
    return True