"""SMTP email sender with TLS and session-level idempotency protection."""

from email.message import EmailMessage as MIMEEmail
import os
import smtplib
import ssl

from pydantic import EmailStr, TypeAdapter
from dotenv import load_dotenv

from email_agent.models import EmailMessage, SendResult


_EMAIL_ADAPTER = TypeAdapter(EmailStr)


class SMTPEmailSender:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        from_email: str,
        username: str | None = None,
        password: str | None = None,
        use_ssl: bool = False,
        timeout: float = 20.0,
    ) -> None:
        self.host = host.strip()
        self.port = port
        self.from_email = from_email.strip()
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.timeout = timeout
        self._sent: dict[str, SendResult] = {}

    def _validate_configuration(self) -> None:
        if not self.host:
            raise ValueError("SMTP_HOST must be configured before sending.")
        if not 1 <= self.port <= 65_535:
            raise ValueError("SMTP_PORT must be between 1 and 65535.")
        if not self.from_email:
            raise ValueError("SMTP_FROM_EMAIL must be configured before sending.")
        if bool(self.username) != bool(self.password):
            raise ValueError("Configure both SMTP_USERNAME and SMTP_PASSWORD, or neither.")
        self.from_email = str(_EMAIL_ADAPTER.validate_python(self.from_email))

    @classmethod
    def from_env(cls) -> "SMTPEmailSender":
        load_dotenv()
        host = os.getenv("SMTP_HOST", "")
        from_email = os.getenv("SMTP_FROM_EMAIL", "")
        username = os.getenv("SMTP_USERNAME") or None
        password = os.getenv("SMTP_PASSWORD") or None
        use_ssl = os.getenv("SMTP_USE_SSL", "false").strip().lower() in {
            "1", "true", "yes", "on"
        }
        return cls(
            host=host,
            port=int(os.getenv("SMTP_PORT", "587")),
            from_email=from_email,
            username=username,
            password=password,
            use_ssl=use_ssl,
        )

    def send_reply(
        self,
        message: EmailMessage,
        body: str,
        *,
        recipient_email: str,
        idempotency_key: str,
    ) -> SendResult:
        if idempotency_key in self._sent:
            return self._sent[idempotency_key]
        if not body.strip():
            raise ValueError("Refusing to send an empty response.")

        self._validate_configuration()
        recipient = str(_EMAIL_ADAPTER.validate_python(recipient_email))
        subject = message.subject.strip()
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}" if subject else "Your email"

        provider_message_id = f"<{idempotency_key}@{self.host}>"
        outbound = MIMEEmail()
        outbound["From"] = self.from_email
        outbound["To"] = recipient
        outbound["Subject"] = subject
        outbound["Message-ID"] = provider_message_id
        outbound["X-Agent-Idempotency-Key"] = idempotency_key
        outbound.set_content(body)

        context = ssl.create_default_context()
        if self.use_ssl:
            server = smtplib.SMTP_SSL(
                self.host, self.port, timeout=self.timeout, context=context
            )
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)

        with server:
            if not self.use_ssl:
                server.starttls(context=context)
            if self.username and self.password:
                server.login(self.username, self.password)
            server.send_message(outbound)

        result = SendResult(
            provider_message_id=provider_message_id,
            idempotency_key=idempotency_key,
            recipient_email=recipient,
        )
        self._sent[idempotency_key] = result
        return result
