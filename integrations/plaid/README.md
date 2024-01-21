Plaid was set up from the pattern guide shown below.

https://github.com/plaid/pattern (last aligned 1/21/2024)

There are 2 docker files in the folder that are used

- client
- server

To run dockerfile and create own image `docker build --no-cache -t docker-plaid-client:latest .` 
To run dockerfile and create own image `docker build --no-cache -t docker-plaid-server:latest .` 

# RUN LOCALLY

If wanting to run the integration in development npm needs to be installed.

Then from the root directory run

```bash
npm start
```

If looking to update packages, the following command reviews outdated packages

```bash
npm outdated
```

to install the latest package

```bash
npm install [package]@latest
```

## CLIENT
If running on windows the `package.json` needs to be update to be compatiable with windows.

from:
```json
"start": "PORT=3001 react-scripts start",
"proxy": "http://server:5001"
```

to:
```json
"start": "set PORT=3001 && react-scripts start",
"proxy": "http://<ip server>:5001"
```

packages that can't be updated without a rewrite
- date-fns: function distanceInWords  doesn't exist
- react-router-dom: needs to be rewritten
- react-toastify: needs to be rewritten
- plaid: the formats are not lining up
- plaid-threads: the formats are not lining up


## SERVER
If running on window the `index.js` should be updated to run locally

from
```
const { PORT } = process.env;
```

to
```
const { PORT } = 5001;
```

packages that can't be updated without a rewrite
- plaid
- node-fetch: there needs to be a change to import