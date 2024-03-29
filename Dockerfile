#FROM node:18
#FROM node:18-slim
FROM node:slim

WORKDIR /src

RUN apt-get update -y -qq
RUN apt-get install -y -qq libgconf-2-4 libatk1.0-0 libatk-bridge2.0-0 libgdk-pixbuf2.0-0 libgtk-3-0 libgbm-dev libnss3-dev libxss-dev libasound2

RUN apt-get install -y -qq nano locales python3 python3-pip python3-venv
RUN pip install --upgrade pip --break-system-packages
RUN pip install Flask --break-system-packages

RUN sed -i '/en_EN.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG en_EN.UTF-8
ENV LANGUAGE en_EN:en

ADD ./src/* ./
RUN sed -i -e 's/\r$//' *sh

RUN npm install

RUN chmod +x flask_start.sh
#CMD ["/bin/bash"]
CMD ["./flask_start.sh"]
