# The python version
FROM python:3.10-slim-buster

COPY . .

ARG USERNAME=ashot
ARG USER_UID=1000
ARG USER_GID=$USER_UID
ARG GROUP=Group

# Create the user
RUN groupadd -g ${USER_GID} ${GROUP} && useradd -u ${USER_UID} -g ${GROUP} -s /bin/sh ${USERNAME}
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt --no-cache-dir

USER $USERNAME

CMD ["python", "-m", "train"]
