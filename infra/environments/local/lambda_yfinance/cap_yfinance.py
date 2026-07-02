import yfinance as yf
import boto3
from datetime import datetime
import os
import pandas as pd

s3_client = boto3.client(
    "s3", endpoint_url=os.environ.get("AWS_ENDPOINT_URL", "http://localstack:4566")
)


def handler(event, context):
    ticker = "PETR4.SA"
    bucket = "data-extract"

    print(f"Iniciando a extração de dados para o ticker: {ticker}")

    data_1_dia_antes = datetime.now() - pd.Timedelta(days=1)
    data_de_hoje = datetime.now()

    try:
        data = yf.download(ticker, period="10y", interval="1d", end=data_1_dia_antes)

        if data.empty:
            print(f"Nenhum dado encontrado para o ticker: {ticker}")
            return {
                "statusCode": 404,
                "body": f"Nenhum dado encontrado para o ticker: {ticker}",
            }

        # Converte o DataFrame para CSV em memória
        csv_buffer = data.to_csv(index=True)

        file_name = f"raw_{ticker.replace('.SA', '')}.csv"

        key = f"landing/{data_de_hoje.strftime('%d-%m-%Y')}/{file_name}"

        s3_client.put_object(Bucket=bucket, Key=key, Body=csv_buffer)

        print(f"Arquivo {file_name} enviado para o bucket {bucket} com sucesso.")
        return {
            "statusCode": 200,
            "body": f"Arquivo {file_name} enviado para o bucket {bucket} com sucesso.",
        }
    except Exception as e:
        print(f"Erro ao extrair dados para o ticker {ticker}: {str(e)}")
        return {
            "statusCode": 500,
            "body": f"Erro ao extrair dados para o ticker {ticker}: {str(e)}",
        }
