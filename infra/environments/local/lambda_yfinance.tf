# Baixar dependências de forma agnóstica (funciona direto no CMD do Windows)
resource "null_resource" "pip_install_yfinance" {
  triggers = {
    requirements = filemd5("${path.module}/lambda_yfinance/requirements.txt")
  }

  provisioner "local-exec" {
    # Comando direto e sem aspas complexas para o CMD
    command = "cd lambda_yfinance && pip install -r requirements.txt --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.11 --only-binary=:all:"
  }
}

# Compactar a pasta de extração (Nome corrigido aqui)
data "archive_file" "lambda_yfinance_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_yfinance"
  output_path = "${path.module}/lambda_yfinance.zip"

  depends_on = [null_resource.pip_install_yfinance]
}

# Função Lambda de extração
resource "aws_lambda_function" "yfinance_extractor" {
  function_name    = "yfinance_daily_extractor"
  role             = aws_iam_role.lambda_role.arn
  handler          = "cap_yfinance.handler"
  runtime          = "python3.11"
  timeout          = 60 
  
  s3_bucket        = aws_s3_bucket.lambda_artifacts.id
  s3_key           = aws_s3_object.yfinance_code_zip.key

  source_code_hash = data.archive_file.lambda_yfinance_zip.output_base64sha256

  environment {
    variables = {
      AWS_ENDPOINT_URL = "http://localstack:4566"
    }
  }

  depends_on = [aws_s3_object.yfinance_code_zip]
}

# A Regra do EventBridge (O Relógio)
resource "aws_cloudwatch_event_rule" "daily_extraction" {
  name                = "trigger-yfinance-daily"
  description         = "Dispara a coleta do yfinance de segunda a sexta as 18h"
  schedule_expression = "cron(10 21 ? * MON-FRI *)" 
}

# Conectar a regra à Lambda
resource "aws_cloudwatch_event_target" "trigger_lambda" {
  rule      = aws_cloudwatch_event_rule.daily_extraction.name
  target_id = "YFinanceLambda"
  arn       = aws_lambda_function.yfinance_extractor.arn
}

# Permissão para o EventBridge invocar a Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.yfinance_extractor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_extraction.arn
}