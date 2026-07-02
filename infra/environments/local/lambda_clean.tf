# Baixar dependências do Terraform
resource "null_resource" "pip_install_clean" {
  triggers      = {
    requirements = filemd5("${path.module}/lambda_clean/requirements.txt")
  }

  provisioner "local-exec" {
    command = "cd lambda_clean && pip install -r requirements.txt --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.11 --only-binary=:all:"
  }
}

# Zipar o diretório lambda_clean
data "archive_file" "lambda_clean_zip" {
  type          = "zip"
  source_dir    = "${path.module}/lambda_clean"
  output_path   = "${path.module}/lambda_clean.zip"

  depends_on    = [null_resource.pip_install_clean]
}

# Upload do arquivo zip para o S3
resource "aws_s3_object" "clean_code_zip" {
  bucket    = aws_s3_bucket.lambda_artifacts.id
  key       = "s3_data_cleaner.zip"
  source    = data.archive_file.lambda_clean_zip.output_path
  etag      = data.archive_file.lambda_clean_zip.output_md5
}

# Função lambda para limpeza de dados
resource "aws_lambda_function" "clean_data_lambda" {
  function_name = "clean_data_lambda"
  role = aws_iam_role.lambda_role.arn
  handler = "cap_clean.handler"
  runtime = "python3.11"

  # Aumento de recursos por conta do pandas
  timeout = 180
  memory_size = 512

  s3_bucket = aws_s3_bucket.lambda_artifacts.id
  s3_key    = aws_s3_object.clean_code_zip.key
  source_code_hash = data.archive_file.lambda_clean_zip.output_base64sha256

  environment {
    variables = {
      AWS_ENDPOINT_URL = "http://localstack:4566"
    }
  }

  depends_on = [aws_s3_object.clean_code_zip]
}

# Permissão para o bucket S3 "Acordar" a função Lambda
resource "aws_lambda_permission" "allow_s3_to_invoke_cleaner" {
    statement_id  = "AllowExecutionFromS3"
    action = "lambda:InvokeFunction"
    function_name = aws_lambda_function.clean_data_lambda.function_name
    principal = "s3.amazonaws.com"
    source_arn = aws_s3_bucket.data_extract.arn
}

# O gatilho do S3 para invocar a função Lambda quando um novo objeto .csv é carregado no bucket
resource "aws_s3_bucket_notification" "cleaner_trigger" {
    # Seleciona o bucket de origem para o gatilho
    bucket = aws_s3_bucket.data_extract.id

    lambda_function {
      # Escolhe a função Lambda que será invocada pelo gatilho
      lambda_function_arn = aws_lambda_function.clean_data_lambda.arn
      # Define o evento que acionará a função Lambda
      events = ["s3:ObjectCreated:*"]
      # Define o prefixo e sufixo do objeto que acionará a função Lambda
      filter_prefix = "landing/"
      filter_suffix = ".csv"
    }

    depends_on = [aws_lambda_permission.allow_s3_to_invoke_cleaner]
}