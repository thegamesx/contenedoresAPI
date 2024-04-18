#
FROM python

#
WORKDIR /code

#
COPY ./requirements.txt /code/requirements.txt

#
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

#
COPY src/ /code/

#
EXPOSE 8080

#
CMD ["uvicorn", "API:app", "--host", "0.0.0.0", "--port", "80"]