import boto3
import pandas as pd
import io
import urllib.parse
import fastparquet

# Configuração para o LocalStack
s3_client = boto3.client(
    "s3",
    endpoint_url="http://localstack:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)


def handler(event, context):
    try:
        # O S3 conta para a Lambda qual bucket e arquivo dispararam o evento
        bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
        object_key = urllib.parse.unquote_plus(
            event["Records"][0]["s3"]["object"]["key"]
        )

        print(f"Iniciando limpeza do arquivo: {object_key} no bucket {bucket_name}")

        arquivo_temp_csv = "/tmp/dados_brutos.csv"
        parquet_tmp = "/tmp/limpo.parquet"
        
        print("Baixando arquivo CSV físico para o /tmp...")
        s3_client.download_file(bucket_name, object_key, arquivo_temp_csv)
        
        print("Lendo arquivo no Pandas...")
        df = pd.read_csv(arquivo_temp_csv, header=[0, 1], index_col=0)

        # Transformações e limpeza de dados
        # Ajustamos o DataFrame para remover o nível de cabeçalho extra
        df.columns = df.columns.droplevel(1)
        # Ajustamos os nomes das colunas e do índice
        df.columns.name = None
        df.index.name = "Date"
        df = df.reset_index()

        # Aplicação de engenharia de features: cálculo de médias móveis, variações percentuais e indicadores técnicos
        df_ef = df.copy()
        print("Iniciando transformações de features (SMA, EMA, RSI)...")
        # Cálculo das médias móveis simples (SMA) para diferentes janelas de tempo em 5, 10, 20 e 30 dias
        df_ef["SMA_5"] = df_ef["Close"].rolling(window=5).mean()
        df_ef["SMA_15"] = df_ef["Close"].rolling(window=15).mean()
        df_ef["SMA_30"] = df_ef["Close"].rolling(window=30).mean()

        # Cálculo das médias móveis exponenciais (EMA) para diferentes janelas de tempo em 5, 10, 20 e 30 dias
        df_ef["EMA_5"] = df_ef["Close"].ewm(span=5, adjust=False).mean()
        df_ef["EMA_15"] = df_ef["Close"].ewm(span=15, adjust=False).mean()
        df_ef["EMA_30"] = df_ef["Close"].ewm(span=30, adjust=False).mean()

        # Cálculo da variação percentual diária do preço de fechamento e do volume negociado
        df_ef["Variation_pct"] = df_ef["Close"].pct_change()
        df_ef["Vol_variation_pct"] = df_ef["Volume"].pct_change()
        df_ef["Vol_variation_pct_10"] = df_ef["Volume"].pct_change(periods=10)

        # Ajustes na tipagem de dados e adição de colunas para o dia da semana e o mês do ano para o modelo entender padrões sazonais
        df_ef["Date"] = pd.to_datetime(df_ef["Date"])
        # Adicionando colunas para o dia da semana e o mês do ano para o modelo entender padrões sazonais
        df_ef["Day_of_week_num"] = df_ef["Date"].dt.weekday
        df_ef["Month_num"] = df_ef["Date"].dt.month

        # Cálculo do Índice de Força Relativa (RSI) com base na variação do preço de fechamento
        periodo = 14
        # Calculando o ganho e a perda entre o dia atual e o dia anterior
        df_ef["Delta"] = df_ef["Close"].diff()
        # Separamos os ganhos e perdas em colunas distintas, substituindo valores negativos por 0 na coluna de ganhos e valores positivos por 0 na coluna de perdas
        df_ef["Ganho"] = df_ef["Delta"].where(df_ef["Delta"] > 0, 0)
        df_ef["Perda"] = df_ef["Delta"].where(df_ef["Delta"] < 0, 0).abs()
        # Calculamos a média movel exponencial (EMA) dos ganhos e perdas para suavizar os valores e obter uma visão mais clara da tendência de alta ou baixa do ativo
        df_ef["Media_ganho"] = (
            df_ef["Ganho"].ewm(alpha=1 / periodo, adjust=False).mean()
        )
        df_ef["Media_perda"] = (
            df_ef["Perda"].ewm(alpha=1 / periodo, adjust=False).mean()
        )

        # Cálculo do Índice de Força Relativa (RSI) com base nas médias móveis exponenciais dos ganhos e perdas
        df_ef["RS"] = df_ef["Media_ganho"] / df_ef["Media_perda"]
        df_ef["RSI"] = 100 - (100 / (1 + df_ef["RS"]))

        # Removendo colunas desnecessárias do DataFrame
        df_ef = df_ef.drop(
            columns=["Delta", "Ganho", "Perda", "Media_ganho", "Media_perda", "RS"]
        )

        df_clean = df_ef.copy()
        df_clean = df_clean.drop(columns=["High", "Low", "Open", "Date"])
        df_clean = df_clean[
            [
                "Close",
                "Variation_pct",
                "SMA_5",
                "SMA_15",
                "SMA_30",
                "EMA_5",
                "EMA_15",
                "EMA_30",
                "RSI",
                "Volume",
                "Vol_variation_pct",
                "Vol_variation_pct_10",
                "Day_of_week_num",
                "Month_num",
            ]
        ]
        # Retirada de valores nulos do DataFrame resultante
        df_clean.dropna(inplace=True)

        print("Salvando em Parquet...")
        fastparquet.write(parquet_tmp, df_clean)
        # Criando um novo caminho para salvar o arquivo limpo no bucket S3, substituindo 'landing' por 'trusted' e alterando a extensão de '.csv' para '.parquet'
        print("Fazendo upload do Parquet final para a camada Trusted...")
        new_path = (
            object_key.replace("landing", "trusted")
            .replace(".csv", ".parquet")
            .replace("raw_", "clean_")
        )

        s3_client.upload_file(parquet_tmp, bucket_name, new_path)

        print(f"SUCESSO TOTAL! Arquivo salvo no destino: {new_path}")
        return {
            "statusCode": 200,
            "body": f"Arquivo limpo e salvo em: {new_path} no bucket {bucket_name}",
        }

    except Exception as e:
        print(f"Erro ao processar o arquivo: {str(e)}")
        return {"statusCode": 500, "body": f"Erro ao processar o arquivo: {str(e)}"}
