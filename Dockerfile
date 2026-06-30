# Pegamos a imagem do Jupyter com PyTorch que você escolheu
FROM quay.io/jupyter/pytorch-notebook:cuda12-python-3.11.8

# Mudamos para o usuário jovyan (padrão dessa imagem) para instalar o Poetry na pasta dele
USER jovyan

# Comando oficial para instalar o Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Adiciona o Poetry no PATH do container para você conseguir dar os comandos direto
ENV PATH="/home/jovyan/.local/bin:$PATH"

# DIca de ouro: Força o Poetry a usar o Python do próprio container (onde está o PyTorch + GPU)
# em vez de tentar criar um ambiente virtual vazio novo (.venv)
RUN poetry config virtualenvs.create false

# Define a pasta padrão de trabalho
WORKDIR /home/jovyan/work