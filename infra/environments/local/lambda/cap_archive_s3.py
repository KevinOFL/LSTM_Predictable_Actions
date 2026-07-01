import urllib.parse
from datetime import datetime
import os
import boto3

s3_client = boto3.client("s3")


def handler(event, context):
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"], encoding="utf-8")

        # Evita loops: processa apenas se o arquivo estiver na raiz ou pasta de entrada específica
        # Se o arquivo já estiver na estrutura de data, ignora para não rodar infinitamente
        if "/" in key and not key.startswith("landing/"):
            continue

        try:
            # Captura o nome do arquivo
            filename = os.path.basename(key)

            # Captura o nome do arquivo sem a extensão para criar a nova estrutura de pastas
            asset_name = os.path.splitext(filename)[0]

            # Captura a data atual para criar a estrutura de pastas
            current_date = datetime.now().strftime("%d-%m-%Y")

            # Gera a nova chave para o arquivo no bucket S3, incluindo a data e o nome do ativo
            new_key = f"landing/{current_date}/{asset_name}/{filename}"

            print(f"Movendo arquivo {key} para {new_key} no bucket {bucket}")

            # Copia o arquivo para a nova chave e depois deleta o arquivo original
            s3_client.copy_object(
                Bucket=bucket, CopySource={"Bucket": bucket, "Key": key}, Key=new_key
            )

            s3_client.delete_object(Bucket=bucket, Key=key)

        except Exception as e:
            print(f"Erro ao processar o arquivo {key} do bucket {bucket}: {str(e)}")
