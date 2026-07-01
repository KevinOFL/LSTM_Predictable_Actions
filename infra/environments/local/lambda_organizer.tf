# Compactar os arquivos da pasta lambda
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/lambda.zip"
}

# Função Lambda para organizar os arquivos no bucket S3
resource "aws_lambda_function" "s3_organizer" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "s3_organizer"
  role             = aws_iam_role.lambda_role.arn
  handler          = "cap_archive_s3.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
}

# Permissões para o S3 invocar a função Lambda
resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.s3_organizer.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data_extract.arn
}

# Configuração da notificação do bucket S3 (Gatilho)
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.data_extract.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.s3_organizer.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "landing/"
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}