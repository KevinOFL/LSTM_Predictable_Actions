import logging
import os
import sys


def configure_logger(aplication_name: str) -> logging.Logger:
    """
    Configura um logger para a aplicação, permitindo o registro de mensagens de log em um arquivo e no console.

    parâmetros:
    - aplication_name (str): O nome da aplicação, usado para nomear o arquivo de log.

    retorno:
    - logging.Logger: O logger configurado para a aplicação.
    """

    logger = logging.getLogger(aplication_name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(module)s | %(message)s"
        )

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_path = os.path.join(base_dir, "logs", f"{aplication_name}.log")

        # Garante que a pasta logs existe
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        file_handler = logging.FileHandler(log_path)  # Onde os logs serão salvos
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler(sys.stdout)  # Log no console
        stream_handler.setFormatter(formatter)

        # Adiciona os handlers ao logger
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger


logger_aws_lambda = configure_logger("aws_lambda")
logger_training = configure_logger("training")
logger_data_processing = configure_logger("data_processing")