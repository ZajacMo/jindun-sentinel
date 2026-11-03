# The JinDun Sentinel web front end.
#
# The build reads three directories from the repository: the front end itself,
# the shared locale catalogue and the methodology documents.  All three are
# read at build time — the catalogue through the Vite plugin, the documents
# through a raw import — so the documentation on screen is the documentation
# that is in the repository, with no second copy to keep in step.

FROM node:22-alpine AS build

WORKDIR /src

COPY packages/web ./packages/web
COPY locales ./locales
COPY docs ./docs

WORKDIR /src/packages/web

# The front end calls the API on its own origin and nginx proxies it, so the
# base URL is a single slash.
ARG VITE_API_BASE=/
ENV VITE_API_BASE=$VITE_API_BASE

RUN npm ci && npm run build


FROM nginx:1.27-alpine

COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/packages/web/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
