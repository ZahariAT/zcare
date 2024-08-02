FROM python:3.11-slim
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
# RUN python -m spacy download en_core_web_sm
RUN python -c "import nltk;nltk.download('punkt')"
RUN python -c "import nltk;nltk.download('wordnet')"
RUN python -c "import nltk;nltk.download('stopwords')"
# RUN python -m nltk.downloader punkt wordnet stopwords
COPY . /code/
