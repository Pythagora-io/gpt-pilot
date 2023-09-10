FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m venv pilot-env
RUN source pilot-env/bin/activate
RUN pip install -r requirements.txt
RUN python ./pilot/db_init.py

CMD [ "python", "./pilot/main.py" ]
