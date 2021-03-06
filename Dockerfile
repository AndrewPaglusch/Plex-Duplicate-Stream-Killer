FROM python:3-alpine

# Install dependencies
RUN apk add --no-cache gettext

# Make a folder to run it in
RUN mkdir /app

# Work from this directory
WORKDIR /app/

# Copy the files
COPY /app/ /app/

# Install python dependencies
RUN pip install -r requirements.txt

ENTRYPOINT ["/bin/ash", "/app/entrypoint.sh"]
