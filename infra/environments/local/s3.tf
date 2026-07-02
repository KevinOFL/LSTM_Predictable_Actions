# Bucket para os artefatos do MLflow
resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = "mlflow-artifacts"

  tags = {
    Name        = "MLflow Artifacts"
    Environment = "Local"
  }
}

# Bucket para os dados extraidos do yfinance
resource "aws_s3_bucket" "data_extract" {
  bucket        = "data-extract"
  force_destroy = true

  tags = {
    Name        = "Data Extract"
    Environment = "Local"
    Description = "Bucket para armazenar os dados extraidos do yfinance"
  }
}

# Bucket dedicado para os artefatos do Lambda
resource "aws_s3_bucket" "lambda_artifacts" {
  bucket        = "lambda-deploy-artifacts"
  force_destroy = true
}

# Faz o upload do arquivo .zip pesadão para o S3
resource "aws_s3_object" "yfinance_code_zip" {
  bucket = aws_s3_bucket.lambda_artifacts.id
  key    = "yfinance_daily_extractor.zip"
  source = data.archive_file.lambda_yfinance_zip.output_path
  
  # O etag garante que o Terraform faça upload de novo se o código mudar
  etag   = data.archive_file.lambda_yfinance_zip.output_md5
}