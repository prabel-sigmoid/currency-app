# Use latest Node LTS
FROM node:22-alpine

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Build the production-ready app
RUN npm run build

# Install 'serve' globally to host the built files
RUN npm install -g serve

# Expose Vite/React default port
EXPOSE 5173

# Serve the build output
CMD ["serve", "-s", "dist", "-l", "5173"]
