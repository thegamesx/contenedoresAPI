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
ARG SUPABASE_URL
ENV supabase_url $SUPABASE_URL
ARG SUPABASE_KEY
ENV supabase_key $SUPABASE_KEY

#
CMD ["fastapi", "run", "src/API.py", "--port", "8080"]