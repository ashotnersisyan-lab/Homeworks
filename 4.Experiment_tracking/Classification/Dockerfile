# The python version
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt to do the package installation
COPY Classification/requirements.txt /app

#ARG USERNAME=ashot
#ARG USER_UID=1000
#ARG USER_GID=$USER_UID
#ARG GROUP=Group

# Create the user
#RUN groupadd -g ${USER_GID} ${GROUP} && useradd -u ${USER_UID} -g ${GROUP} -s /bin/sh ${USERNAME}
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt --no-cache-dir

# Copy the current directory contents into the container
COPY Classification/data /app
COPY Classification/train.py /app

#USER $USERNAME

CMD ["python", "-m", "train"]
