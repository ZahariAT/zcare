FROM python:3.11-slim
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "import nltk;nltk.download('punkt')"
RUN python -c "import nltk;nltk.download('wordnet')"
RUN python -c "import nltk;nltk.download('stopwords')"
COPY . /code/
