FROM node:20-alpine

WORKDIR /app/theme

COPY ./theme/package.json ./theme/package-lock.json* ./
RUN npm install

CMD ["npm", "run", "watch"]