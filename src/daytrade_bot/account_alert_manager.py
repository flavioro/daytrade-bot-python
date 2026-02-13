import smtplib
import requests
import winsound
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def check_equity_and_alert(config, logger, equity):
    """Verifica equity e envia alertas se atingir o alvo definido."""

    target = config.get("equity_target", 0)

    logger.info(f"[EQUITY CHECK] Equity atual: {equity:.2f} | Target: {target:.2f}")

    if equity >= target and target > 0:
        logger.warning(f"[ALERTA] Equity atingiu {equity:.2f}, igual/superior ao alvo {target:.2f}")
        message = f"""
        ⚠️ ALERTA DE EQUITY ⚠️

        Equity atual: {equity:.2f}
        Alvo configurado: {target:.2f}
        Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        Recomenda-se verificar a conta e realizar o saque.
        """

        # Enviar e-mail
        if config.get("send_email", False):
            send_email_alert(config["email_settings"], message, logger)

        # Enviar Telegram
        if config.get("send_telegram", False):
            send_telegram_alert(config["telegram_settings"], message, logger)

        # Emitir som local
        if config.get("alarm_sound", False):
            play_alarm_sound()

def send_email_alert(settings, message, logger):
    """Envia e-mail de alerta via Gmail."""
    try:
        msg = MIMEMultipart()
        msg["From"] = settings["from"]
        msg["To"] = ", ".join(settings["to"])
        msg["Subject"] = "🚨 Alerta de Equity MT5"

        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings["from"], settings["password"])
            server.send_message(msg)

        logger.info("E-mail de alerta enviado com sucesso.")
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail: {e}")

def send_telegram_alert(settings, message, logger):
    """Envia mensagem de alerta via Telegram."""
    try:
        token = settings["bot_token"]
        chat_id = settings["chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        requests.post(url, data=payload)
        logger.info("Mensagem enviada ao Telegram com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao enviar alerta Telegram: {e}")

def play_alarm_sound():
    """Reproduz som local de alerta."""
    try:
        winsound.Beep(1000, 3000)  # Frequência 1000Hz, duração 3s
        winsound.Beep(1200, 2000)
        winsound.Beep(1400, 1000)
    except Exception:
        pass
