import { app } from '@server/app';

export default {
  hostname: '127.0.0.1',
  port: 9001,
  fetch: app.fetch,
};
